import os
from datetime import datetime, date, timedelta
from app import create_app
from models import db, User, Transaction, Budget, StockHolding

def seed_database():
    app = create_app()
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()
        
        print("Inserting demo user...")
        user = User(
            username="demouser",
            email="demo@financeapp.com",
            base_currency="GBP"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        print(f"Created demo user: {user.username} (ID: {user.id})")
        
        print("Seeding monthly budgets...")
        budgets = [
            Budget(user_id=user.id, category="Groceries", monthly_limit=300.00),
            Budget(user_id=user.id, category="Entertainment", monthly_limit=150.00),
            Budget(user_id=user.id, category="Transport", monthly_limit=150.00),
            Budget(user_id=user.id, category="Bills", monthly_limit=650.00)
        ]
        db.session.add_all(budgets)
        
        print("Seeding 6 months of historical transactions...")
        transactions = []
        
        start_date = date(2025, 11, 25)
        end_date = date(2026, 5, 22)
        
        current_dt = start_date
        while current_dt <= end_date:
            # salary
            is_may_2026 = (current_dt.month == 5 and current_dt.year == 2026)
            salary_day = 1 if is_may_2026 else 28
            if current_dt.day == salary_day:
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=2100.00 if is_may_2026 else 3200.00,
                    description="Monthly Salary - May" if is_may_2026 else "Monthly TechCorp Salary Transfer",
                    category="Salary",
                    type="income",
                    currency="GBP",
                    notes="Direct payroll deposit"
                ))
            
            # rent
            if current_dt.day == 1:
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=500.00,
                    description="Residential Rental Transfer",
                    category="Bills",
                    type="expense",
                    currency="GBP",
                    notes="Automated standing order"
                ))
                
            # utilities
            if current_dt.day == 5:
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=120.00,
                    description="British Gas Utilities standing order",
                    category="Bills",
                    type="expense",
                    currency="GBP"
                ))
                
            # gym
            if current_dt.day == 10:
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=45.00,
                    description="PureGym London Monthly Membership",
                    category="Entertainment",
                    type="expense",
                    currency="GBP"
                ))
                
            # phone
            if current_dt.day == 15:
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=35.00,
                    description="EE Mobile Monthly Direct Debit",
                    category="Bills",
                    type="expense",
                    currency="GBP"
                ))
                
            # groceries
            if current_dt.weekday() == 5:  # Saturday
                if current_dt.day % 2 == 0:
                    transactions.append(Transaction(
                        user_id=user.id,
                        date=current_dt,
                        amount=65.40,
                        description="Tesco Superstore Grocery Run",
                        category="Groceries",
                        type="expense",
                        currency="GBP"
                    ))
                else:
                    transactions.append(Transaction(
                        user_id=user.id,
                        date=current_dt,
                        amount=58.20,
                        description="Sainsbury's Food & Veg",
                        category="Groceries",
                        type="expense",
                        currency="GBP"
                    ))
                    
            # transport
            if current_dt.weekday() == 4:  # Friday
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=28.50,
                    description="Transport for London contactless charge",
                    category="Transport",
                    type="expense",
                    currency="GBP"
                ))
                
            # dinners / fun
            if current_dt.day in [3, 12, 21, 27] and current_dt.weekday() >= 4:  # Fri/Sat/Sun
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=42.00,
                    description="The Botanist Cocktail & Dinner",
                    category="Entertainment",
                    type="expense",
                    currency="GBP"
                ))
            
            # amazon etc
            if current_dt.day == 18 and current_dt.month in [12, 2, 4]:
                transactions.append(Transaction(
                    user_id=user.id,
                    date=current_dt,
                    amount=89.99,
                    description="Amazon UK online purchase",
                    category="Other",
                    type="expense",
                    currency="GBP"
                ))
                
            current_dt += timedelta(days=1)
            
        db.session.add_all(transactions)
        
        # stocks
        holdings = [
            StockHolding(user_id=user.id, ticker="AAPL", shares=10.0, purchase_price=175.50),
            StockHolding(user_id=user.id, ticker="MSFT", shares=8.0, purchase_price=385.00),
            StockHolding(user_id=user.id, ticker="TSLA", shares=15.0, purchase_price=170.20),
            StockHolding(user_id=user.id, ticker="VOD.L", shares=500.0, purchase_price=0.6840)  # VOD.L is in GBP/LSE units
        ]
        db.session.add_all(holdings)
        
        db.session.commit()
        print("Database successfully seeded with realistic sample data!")

if __name__ == "__main__":
    seed_database()
