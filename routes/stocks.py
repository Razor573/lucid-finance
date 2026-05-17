from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import yfinance as yf
from models import db, StockHolding, StockCache
from forms import StockForm
from utils.stock_fetcher import get_cached_rate, convert_currency
from utils.rate_limiter import rate_limit

stocks_bp = Blueprint('stocks', __name__, url_prefix='/stocks')

@stocks_bp.route('/', methods=['GET'])
@login_required
def view_portfolio():
    form = StockForm()
    holdings = StockHolding.query.filter_by(user_id=current_user.id).all()
    
    stats = {
        'total_invested': 0.0,
        'current_value': 0.0,
        'net_return': 0.0,
        'return_percent': 0.0
    }
    holdings_data = []
    
    for h in holdings:
        try:
            current_price, asset_currency = get_cached_rate(h.ticker, db.session)
            shares = float(h.shares)
            price = float(h.purchase_price)
            
            cost_basis = convert_currency(price, asset_currency, current_user.base_currency, db.session)
            invested_base = cost_basis * shares
            
            curr_price_base = convert_currency(current_price, asset_currency, current_user.base_currency, db.session)
            curr_val_base = curr_price_base * shares
            
            net_ret = curr_val_base - invested_base
            return_pct = (net_ret / invested_base * 100) if invested_base > 0 else 0.0
            
            holdings_data.append({
                'id': h.id,
                'ticker': h.ticker,
                'shares': shares,
                'purchase_price': price,
                'purchase_price_base': cost_basis,
                'current_price': current_price,
                'current_price_base': curr_price_base,
                'total_invested_base': invested_base,
                'current_value_base': curr_val_base,
                'net_return_base': net_ret,
                'return_percent': return_pct,
                'currency': asset_currency
            })
            stats['total_invested'] += invested_base
            stats['current_value'] += curr_val_base
            
        except Exception as e:
            shares = float(h.shares)
            price = float(h.purchase_price)
            cost_basis = price
            invested_base = cost_basis * shares
            
            holdings_data.append({
                'id': h.id,
                'ticker': h.ticker,
                'shares': shares,
                'purchase_price': price,
                'purchase_price_base': cost_basis,
                'current_price': price,
                'current_price_base': cost_basis,
                'total_invested_base': invested_base,
                'current_value_base': invested_base,
                'net_return_base': 0.0,
                'return_percent': 0.0,
                'currency': current_user.base_currency,
                'error': str(e)
            })
            stats['total_invested'] += invested_base
            stats['current_value'] += invested_base
            
    stats['net_return'] = stats['current_value'] - stats['total_invested']
    if stats['total_invested'] > 0:
        stats['return_percent'] = (stats['net_return'] / stats['total_invested']) * 100
        
    return render_template(
        'stocks.html',
        form=form,
        holdings=holdings_data,
        stats=stats,
        base_currency=current_user.base_currency
    )

@stocks_bp.route('/add', methods=['POST'])
@login_required
@rate_limit(limit=10, period=60)
def add_holding():
    form = StockForm()
    if form.validate_on_submit():
        ticker = form.ticker.data.upper().strip()
        shares = float(form.shares.data)
        purchase_price = float(form.purchase_price.data)
        
        try:
            get_cached_rate(ticker, db.session)
        except ValueError:
            flash('Invalid stock ticker symbol', 'danger')
            return redirect(url_for('stocks.view_portfolio'))
        except Exception:
            flash(
                'An error occurred fetching market data. Please try again later.',
                'danger'
            )
            return redirect(url_for('stocks.view_portfolio'))
            
        existing = StockHolding.query.filter_by(user_id=current_user.id, ticker=ticker).first()
        if existing:
            old_shares = float(existing.shares)
            old_price = float(existing.purchase_price)
            
            new_shares = old_shares + shares
            total_cap = (old_shares * old_price) + (shares * purchase_price)
            avg_price = total_cap / new_shares
            
            existing.shares = new_shares
            existing.purchase_price = avg_price
            flash(f"Updated existing asset holding of {ticker}! Added {shares} shares and adjusted weighted cost basis.", 'success')
        else:
            new_holding = StockHolding(
                user_id=current_user.id,
                ticker=ticker,
                shares=shares,
                purchase_price=purchase_price
            )
            db.session.add(new_holding)
            flash(f"Added {shares} shares of {ticker} to your portfolio!", 'success')
            
        db.session.commit()
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
                
    return redirect(url_for('stocks.view_portfolio'))

@stocks_bp.route('/delete/<int:holding_id>', methods=['POST'])
@login_required
def delete_holding(holding_id):
    holding = StockHolding.query.filter_by(id=holding_id, user_id=current_user.id).first_or_404()
    ticker = holding.ticker
    db.session.delete(holding)
    db.session.commit()
    flash(f"Deleted {ticker} holding from portfolio.", 'success')
    return redirect(url_for('stocks.view_portfolio'))

@stocks_bp.route('/api/history/<ticker>', methods=['GET'])
@login_required
@rate_limit(limit=20, period=60)
def api_stock_history(ticker):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        
        if hist.empty:
            return jsonify({'labels': [], 'prices': []})
            
        currency = stock.fast_info.currency or 'USD'
        prices = list(hist['Close'])
        labels = [d.strftime('%Y-%m-%d') for d in hist.index]
        
        if currency in ['GBp', 'GBX']:
            prices = [p / 100.0 for p in prices]
            currency = 'GBP'
            
        try:
            if currency != current_user.base_currency:
                pair = f"{currency}{current_user.base_currency}=X"
                rate, _ = get_cached_rate(pair, db.session)
                prices = [round(p * rate, 2) for p in prices]
                currency = current_user.base_currency
            else:
                prices = [round(p, 2) for p in prices]
        except Exception:
            prices = [round(p, 2) for p in prices]
            
        return jsonify({
            'labels': labels,
            'prices': prices,
            'currency': currency
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
