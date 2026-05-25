from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_user, logout_user, login_required, current_user
import csv
import io
from models import db, User, Transaction, Budget, StockHolding
from forms import RegisterForm, LoginForm, SettingsForm
from utils.rate_limiter import rate_limit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.view_dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(limit=5, period=60)
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.view_dashboard'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        email_exist = User.query.filter_by(email=form.email.data.lower()).first()
        user_exist = User.query.filter_by(username=form.username.data).first()
        
        if email_exist:
            flash('An account with this email already exists.', 'danger')
            return render_template('register.html', form=form)
        if user_exist:
            flash('Username is already taken.', 'danger')
            return render_template('register.html', form=form)
            
        new_user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            base_currency=form.base_currency.data
        )
        new_user.set_password(form.password.data)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(limit=5, period=60)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.view_dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('dashboard.view_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html', form=form)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    # csrf is validated automatically
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        existing_username = User.query.filter(User.username == form.username.data, User.id != current_user.id).first()
        existing_email = User.query.filter(User.email == form.email.data.lower(), User.id != current_user.id).first()
        
        if existing_username:
            flash('Username is already taken.', 'danger')
        elif existing_email:
            flash('Email is already registered.', 'danger')
        else:
            current_user.username = form.username.data
            current_user.email = form.email.data.lower()
            current_user.base_currency = form.base_currency.data
            db.session.commit()
            flash('Your settings have been updated.', 'success')
            return redirect(url_for('auth.settings'))
            
    return render_template('settings.html', form=form)

@auth_bp.route('/settings/export/transactions', methods=['GET'])
@login_required
def export_transactions():
    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['Date', 'Amount', 'Description', 'Category', 'Type', 'Currency', 'Notes'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        
        for t in txs:
            writer.writerow([t.date.strftime('%Y-%m-%d'), float(t.amount), t.description, t.category, t.type, t.currency, t.notes or ''])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
            
    response = Response(generate(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="lucid_finance_transactions.csv")
    return response

@auth_bp.route('/settings/reset', methods=['POST'])
@login_required
def reset_data():
    Transaction.query.filter_by(user_id=current_user.id).delete()
    Budget.query.filter_by(user_id=current_user.id).delete()
    StockHolding.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All account data has been successfully cleared.', 'warning')
    return redirect(url_for('auth.settings'))
