from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegisterForm, LoginForm
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
