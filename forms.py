# WTForms configurations for inputs

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, DecimalField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, EqualTo
from datetime import date

CURRENCY_CHOICES = [('GBP', 'GBP (£)'), ('USD', "USD ($)"), ('EUR', 'EUR (€)')]
CATEGORY_CHOICES = [
    ('Groceries', 'Groceries'),
    ('Transport', 'Transport'),
    ('Entertainment', 'Entertainment'),
    ('Bills', 'Bills'),
    ('Salary', 'Salary'),
    ('Other', 'Other')
]
BUDGET_CATEGORY_CHOICES = [
    ('Groceries', 'Groceries'),
    ('Transport', 'Transport'),
    ('Entertainment', 'Entertainment'),
    ('Bills', 'Bills'),
    ('Other', 'Other')
]
TYPE_CHOICES = [('expense', 'Expense'), ('income', 'Income')]

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, max=150)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    base_currency = SelectField('Base Currency', choices=CURRENCY_CHOICES, default='GBP', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class TransactionForm(FlaskForm):
    date = DateField('Date', default=date.today, validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = StringField('Description', validators=[DataRequired(), Length(max=255)])
    category = SelectField('Category', choices=CATEGORY_CHOICES, default='Other', validators=[DataRequired()])
    type = SelectField('Type', choices=TYPE_CHOICES, default='expense', validators=[DataRequired()])
    currency = SelectField('Currency', choices=CURRENCY_CHOICES, default='GBP', validators=[DataRequired()])
    notes = StringField('Notes / Reference', validators=[Length(max=255)])
    submit = SubmitField('Save Transaction')

class BudgetForm(FlaskForm):
    category = SelectField('Category', choices=BUDGET_CATEGORY_CHOICES, validators=[DataRequired()])
    monthly_limit = DecimalField('Monthly Limit', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Save Budget')

class StockForm(FlaskForm):
    ticker = StringField('Stock Ticker', validators=[DataRequired(), Length(min=1, max=10)])
    shares = DecimalField('Shares Quantity', validators=[DataRequired(), NumberRange(min=0.0001)])
    purchase_price = DecimalField('Purchase Price (Asset Currency)', validators=[DataRequired(), NumberRange(min=0.01)])
    submit = SubmitField('Save Holding')

class CSVUploadForm(FlaskForm):
    csv_file = FileField('Bank Statement CSV', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload CSV')

class LogoutForm(FlaskForm):
    submit = SubmitField('Log Out')
