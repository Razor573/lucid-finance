from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    base_currency = db.Column(db.String(3), default='GBP', nullable=False)
    
    # relations
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    budgets = db.relationship('Budget', backref='user', lazy=True, cascade="all, delete-orphan")
    stock_holdings = db.relationship('StockHolding', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='Other', nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    currency = db.Column(db.String(3), default='GBP', nullable=False)
    notes = db.Column(db.String(255), nullable=True)

class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    monthly_limit = db.Column(db.Numeric(12, 2), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category', name='_user_category_budget_uc'),
    )

class StockHolding(db.Model):
    __tablename__ = 'stock_holdings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Numeric(16, 4), nullable=False)
    purchase_price = db.Column(db.Numeric(12, 2), nullable=False)
    date_added = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'ticker', name='_user_ticker_stock_uc'),
    )

class StockCache(db.Model):
    __tablename__ = 'stock_cache'
    
    ticker = db.Column(db.String(15), primary_key=True)
    cached_price = db.Column(db.Numeric(16, 4), nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    last_fetched = db.Column(db.DateTime, nullable=False)
