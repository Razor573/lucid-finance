import os
import json
import base64
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Transaction
from forms import TransactionForm, CSVUploadForm
from utils.csv_parser import scan_csv_headers, parse_mapped_csv
from utils.rate_limiter import rate_limit

transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

@transactions_bp.route('/', methods=['GET'])
@login_required
def view_transactions():
    search = request.args.get('search', '').strip()
    cat_filter = request.args.get('category', '').strip()
    t_filter = request.args.get('type', '').strip()
    
    query = Transaction.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))
    if cat_filter:
        query = query.filter_by(category=cat_filter)
    if t_filter:
        query = query.filter_by(type=t_filter)
        
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=15, error_out=False)
    transactions = pagination.items
    
    tx_form = TransactionForm()
    csv_form = CSVUploadForm()
    categories = ['Groceries', 'Transport', 'Entertainment', 'Bills', 'Salary', 'Other']
    
    return render_template(
        'transactions.html',
        transactions=transactions,
        pagination=pagination,
        tx_form=tx_form,
        csv_form=csv_form,
        categories=categories,
        search=search,
        selected_category=cat_filter,
        base_currency=current_user.base_currency
    )

@transactions_bp.route('/add', methods=['POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        tx = Transaction(
            user_id=current_user.id,
            date=form.date.data,
            amount=form.amount.data,
            description=form.description.data,
            category=form.category.data,
            type=form.type.data,
            currency=form.currency.data,
            notes=form.notes.data or None
        )
        db.session.add(tx)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
    else:
        for f, errs in form.errors.items():
            for e in errs:
                flash(f"Error in {getattr(form, f).label.text}: {e}", 'danger')
    return redirect(url_for('transactions.view_transactions'))

@transactions_bp.route('/edit/<int:tx_id>', methods=['POST'])
@login_required
def edit_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    form = TransactionForm()
    if form.validate_on_submit():
        tx.date = form.date.data
        tx.amount = form.amount.data
        tx.description = form.description.data
        tx.category = form.category.data
        tx.type = form.type.data
        tx.currency = form.currency.data
        tx.notes = form.notes.data or None
        
        db.session.commit()
        flash('Transaction updated successfully!', 'success')
    else:
        for f, errs in form.errors.items():
            for e in errs:
                flash(f"Error in {getattr(form, f).label.text}: {e}", 'danger')
    return redirect(url_for('transactions.view_transactions'))

@transactions_bp.route('/delete/<int:tx_id>', methods=['POST'])
@login_required
def delete_transaction(tx_id):
    tx = Transaction.query.filter_by(id=tx_id, user_id=current_user.id).first_or_404()
    db.session.delete(tx)
    db.session.commit()
    flash('Transaction deleted successfully.', 'success')
    return redirect(url_for('transactions.view_transactions'))

@transactions_bp.route('/upload-scan', methods=['POST'])
@login_required
@rate_limit(limit=5, period=60)
def upload_scan():
    form = CSVUploadForm()
    if form.validate_on_submit():
        csv_file = form.csv_file.data
        try:
            bytes_data = csv_file.read()
            text_data = bytes_data.decode('utf-8', errors='replace')
            headers, err = scan_csv_headers(io.StringIO(text_data))
        except Exception as e:
            flash(f"Failed to read CSV: {str(e)}", 'danger')
            return redirect(url_for('transactions.view_transactions'))
            
        if err:
            flash(err, 'danger')
            return redirect(url_for('transactions.view_transactions'))
            
        defaults = {
            'date': '', 'amount': '', 'description': '', 'category': '', 'type': '', 'notes': ''
        }
        for h in headers:
            h_low = h.lower()
            if any(w in h_low for w in ['date', 'time', 'timestamp']):
                defaults['date'] = h
            elif any(w in h_low for w in ['amount', 'val', 'cost', 'price', 'sum']):
                defaults['amount'] = h
            elif any(w in h_low for w in ['desc', 'name', 'payee', 'merchant', 'detail', 'transaction']):
                defaults['description'] = h
            elif any(w in h_low for w in ['cat', 'group', 'tag']):
                defaults['category'] = h
            elif any(w in h_low for w in ['type', 'direction', 'cr/dr']):
                defaults['type'] = h
            elif any(w in h_low for w in ['note', 'ref', 'memo', 'comment']):
                defaults['notes'] = h
                
        b64_data = base64.b64encode(bytes_data).decode('utf-8')
        return render_template('csv_map.html', headers=headers, defaults=defaults, csv_b64=b64_data)
        
    flash('Please upload a valid CSV file.', 'danger')
    return redirect(url_for('transactions.view_transactions'))

@transactions_bp.route('/upload-preview', methods=['POST'])
@login_required
@rate_limit(limit=5, period=60)
def upload_preview():
    csv_b64 = request.form.get('csv_b64')
    if not csv_b64:
        flash('Statement upload session has expired. Please re-upload.', 'danger')
        return redirect(url_for('transactions.view_transactions'))
        
    mapping = {
        'date': request.form.get('map_date'),
        'amount': request.form.get('map_amount'),
        'description': request.form.get('map_description'),
        'category': request.form.get('map_category'),
        'type': request.form.get('map_type'),
        'notes': request.form.get('map_notes')
    }
    
    if not mapping['date'] or not mapping['amount'] or not mapping['description']:
        flash('Date, Amount, and Description mapping columns are mandatory.', 'danger')
        return redirect(url_for('transactions.view_transactions'))
        
    try:
        bytes_data = base64.b64decode(csv_b64)
        text_data = bytes_data.decode('utf-8', errors='replace')
        parsed_rows, errors = parse_mapped_csv(io.StringIO(text_data), mapping, current_user.base_currency)
    except Exception as e:
        flash(f"Error parsing CSV statement data: {str(e)}", 'danger')
        return redirect(url_for('transactions.view_transactions'))
        
    if errors:
        for err in errors[:5]:
            flash(err, 'warning')
            
    if not parsed_rows:
        flash('No transactions could be successfully validated from the CSV.', 'danger')
        return redirect(url_for('transactions.view_transactions'))
        
    json_rows = []
    for r in parsed_rows:
        json_row = dict(r)
        json_row['date'] = r['date'].strftime('%Y-%m-%d')
        json_row['amount'] = float(r['amount'])
        json_rows.append(json_row)
        
    return render_template('csv_preview.html', transactions=parsed_rows, json_data=json.dumps(json_rows))

@transactions_bp.route('/upload-confirm', methods=['POST'])
@login_required
@rate_limit(limit=5, period=60)
def upload_confirm():
    json_data = request.form.get('transactions_json')
    if not json_data:
        flash('No transaction data to import was provided.', 'danger')
        return redirect(url_for('transactions.view_transactions'))
        
    try:
        transactions = json.loads(json_data)
        import_cnt = 0
        
        for tx in transactions:
            parsed_date = datetime.strptime(tx['date'], '%Y-%m-%d').date()
            new_tx = Transaction(
                user_id=current_user.id,
                date=parsed_date,
                amount=float(tx['amount']),
                description=tx['description'],
                category=tx['category'],
                type=tx['type'],
                currency=tx['currency'],
                notes=tx.get('notes')
            )
            db.session.add(new_tx)
            import_cnt += 1
            
        db.session.commit()
        flash(f"Successfully imported {import_cnt} bank statement transactions!", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error performing statement import: {str(e)}", 'danger')
        
    return redirect(url_for('transactions.view_transactions'))
