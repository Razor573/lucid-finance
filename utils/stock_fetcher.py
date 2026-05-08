import time
from datetime import datetime, timedelta
import yfinance as yf
from models import db, StockCache

CACHE_TTL = 300  # 5 minutes

STATIC_FX_RATES = {
    ('USD', 'GBP'): 0.78,
    ('GBP', 'USD'): 1.28,
    ('EUR', 'GBP'): 0.85,
    ('GBP', 'EUR'): 1.17,
    ('USD', 'EUR'): 0.92,
    ('EUR', 'USD'): 1.09,
}

def get_cached_rate(ticker, db_session):
    ticker = ticker.upper()
    cached = db_session.query(StockCache).filter_by(ticker=ticker).first()
    
    if cached and (datetime.utcnow() - cached.last_fetched) < timedelta(seconds=CACHE_TTL):
        return float(cached.cached_price), cached.currency
        
    try:
        stock = yf.Ticker(ticker)
        price = stock.fast_info.last_price
        
        if price is None or str(price) == 'nan':
            hist = stock.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                raise ValueError("No historical price found.")
                
        currency = stock.fast_info.currency or 'USD'
        
        # UK equities report in pence — convert to pounds
        if currency in ['GBp', 'GBX']:
            price = price / 100.0
            currency = 'GBP'
            
        price_float = float(price)
        
        try:
            entry = db_session.query(StockCache).filter_by(ticker=ticker).first()
            if not entry:
                entry = StockCache(ticker=ticker)
                db_session.add(entry)
            
            entry.cached_price = price_float
            entry.currency = currency
            entry.last_fetched = datetime.utcnow()
            db_session.commit()
            return price_float, currency
        except Exception as commit_exc:
            db_session.rollback()
            db_session.expire_all()
            entry = db_session.query(StockCache).filter_by(ticker=ticker).first()
            if entry:
                return float(entry.cached_price), entry.currency
            raise commit_exc
        
    except Exception as e:
        try:
            db_session.rollback()
        except Exception:
            pass
        try:
            db_session.expire_all()
        except Exception:
            pass
            
        try:
            stale = db_session.query(StockCache).filter_by(ticker=ticker).first()
            if stale:
                return float(stale.cached_price), stale.currency
        except Exception:
            pass
            
        for (fc, tc), rate in STATIC_FX_RATES.items():
            if ticker == f"{fc}{tc}=X":
                return float(rate), tc
                
        raise ValueError(f"Unable to fetch price for ticker {ticker}: {str(e)}")

def convert_currency(amount, from_cur, to_cur, db_session):
    if from_cur == to_cur:
        return amount
        
    from_cur = from_cur.upper()
    to_cur = to_cur.upper()
    
    pair = f"{from_cur}{to_cur}=X"
    try:
        rate, _ = get_cached_rate(pair, db_session)
        return amount * rate
    except Exception:
        inv_pair = f"{to_cur}{from_cur}=X"
        try:
            rate, _ = get_cached_rate(inv_pair, db_session)
            return amount / rate
        except Exception:
            if (from_cur, to_cur) in STATIC_FX_RATES:
                return amount * STATIC_FX_RATES[(from_cur, to_cur)]
            if (to_cur, from_cur) in STATIC_FX_RATES:
                return amount / STATIC_FX_RATES[(to_cur, from_cur)]
                
            raise ValueError(f"Unable to convert from {from_cur} to {to_cur}: FX rate lookup failed.")
