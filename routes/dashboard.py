from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from models import db, Transaction, Budget
from forms import BudgetForm
from utils.stock_fetcher import convert_currency

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def view_dashboard():
    budget_form = BudgetForm()
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    
    if budget_form.validate_on_submit():
        exist_b = Budget.query.filter_by(user_id=current_user.id, category=budget_form.category.data).first()
        if exist_b:
            exist_b.monthly_limit = budget_form.monthly_limit.data
            flash(f"Updated {budget_form.category.data} budget limit!", 'success')
        else:
            new_b = Budget(
                user_id=current_user.id,
                category=budget_form.category.data,
                monthly_limit=budget_form.monthly_limit.data
            )
            db.session.add(new_b)
            flash(f"Created new budget for {budget_form.category.data}!", 'success')
            
        db.session.commit()
        return redirect(url_for('dashboard.view_dashboard'))
        
    today = date.today()
    start_month = date(today.year, today.month, 1)
    
    txs = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_month,
        Transaction.date <= today
    ).all()
    
    total_income = sum(
        convert_currency(float(t.amount), t.currency, current_user.base_currency, db.session)
        for t in txs if t.type == 'income'
    )
    total_expenses = sum(
        convert_currency(float(t.amount), t.currency, current_user.base_currency, db.session)
        for t in txs if t.type == 'expense'
    )
    net_savings = total_income - total_expenses
    
    savings_rate = 0.0
    if total_income > 0:
        savings_rate = (net_savings / total_income) * 100
        
    over_count = 0
    b_stats = []
    
    for b in budgets:
        spent = sum(
            convert_currency(float(t.amount), t.currency, current_user.base_currency, db.session)
            for t in txs if t.type == 'expense' and t.category == b.category
        )
        limit = float(b.monthly_limit)
        is_over = spent > limit
        if is_over:
            over_count += 1
            
        pct = (spent / limit) * 100 if limit > 0 else 0
        b_stats.append({
            'id': b.id,
            'category': b.category,
            'limit': limit,
            'spent': spent,
            'percent': min(pct, 100),
            'actual_percent': pct,
            'over': is_over
        })
        
    today_str = today.strftime('%Y-%m')
    
    return render_template(
        'dashboard.html',
        budget_form=budget_form,
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        savings_rate=savings_rate,
        over_budget_count=over_count,
        budget_stats=b_stats,
        base_currency=current_user.base_currency,
        today_str=today_str
    )

@dashboard_bp.route('/budget/delete/<int:budget_id>', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    category = budget.category
    db.session.delete(budget)
    db.session.commit()
    flash(f"Deleted budget for {category}.", 'success')
    return redirect(url_for('dashboard.view_dashboard'))

@dashboard_bp.route('/api/spending-by-category', methods=['GET'])
@login_required
def api_spending_by_category():
    month_str = request.args.get('month', '')
    today = date.today()
    year, month = today.year, today.month
    if month_str:
        try:
            dt = datetime.strptime(month_str, '%Y-%m').date()
            year, month = dt.year, dt.month
        except ValueError:
            pass
        
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
        
    txs = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    cat_sums = {}
    for t in txs:
        converted_amt = convert_currency(float(t.amount), t.currency, current_user.base_currency, db.session)
        cat_sums[t.category] = cat_sums.get(t.category, 0.0) + converted_amt
        
    labels = list(cat_sums.keys())
    data = [round(cat_sums[k], 2) for k in labels]
    
    if not labels:
        labels = ["No Expenses"]
        data = [0.0]
        
    return jsonify({
        'labels': labels,
        'data': data,
        'month': f"{year:04d}-{month:02d}",
        'currency': current_user.base_currency
    })

@dashboard_bp.route('/api/monthly-trend', methods=['GET'])
@login_required
def api_monthly_trend():
    num_months = request.args.get('months', 6, type=int)
    today = date.today()
    labels = []
    income_data = []
    expense_data = []
    
    cur_y = today.year
    cur_m = today.month
    
    month_keys = []
    for i in range(num_months - 1, -1, -1):
        m = cur_m - i
        y = cur_y
        while m <= 0:
            m += 12
            y -= 1
        month_keys.append((y, m))
        
    first_y, first_m = month_keys[0]
    start_date = date(first_y, first_m, 1)
    
    txs = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= today
    ).all()
    
    buckets = {}
    for (y, m) in month_keys:
        buckets[(y, m)] = {'income': 0.0, 'expense': 0.0}
        
    for t in txs:
        key = (t.date.year, t.date.month)
        if key in buckets:
            converted_amt = convert_currency(float(t.amount), t.currency, current_user.base_currency, db.session)
            if t.type == 'income':
                buckets[key]['income'] += converted_amt
            elif t.type == 'expense':
                buckets[key]['expense'] += converted_amt
                
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    for (y, m) in month_keys:
        labels.append(f"{month_names[m-1]} {str(y)[2:]}")
        income_data.append(round(buckets[(y, m)]['income'], 2))
        expense_data.append(round(buckets[(y, m)]['expense'], 2))
        
    return jsonify({
        'labels': labels,
        'income': income_data,
        'expenses': expense_data,
        'currency': current_user.base_currency
    })

@dashboard_bp.route('/api/budget-status', methods=['GET'])
@login_required
def api_budget_status():
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    today = date.today()
    start_date = date(today.year, today.month, 1)
    
    txs = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= start_date,
        Transaction.date <= today
    ).all()
    
    b_list = []
    for b in budgets:
        spent = sum(
            convert_currency(float(t.amount), t.currency, current_user.base_currency, db.session)
            for t in txs if t.category == b.category
        )
        limit = float(b.monthly_limit)
        b_list.append({
            'category': b.category,
            'limit': limit,
            'spent': round(spent, 2),
            'over': spent > limit
        })
        
    return jsonify({
        'budgets': b_list
    })
