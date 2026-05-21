import io
import json
from datetime import date
from unittest.mock import patch, MagicMock
from models import User, Budget, Transaction, StockHolding, StockCache
from utils.stock_fetcher import get_cached_rate

class MockFastInfo:
    def __init__(self, last_price=150.0, currency='USD'):
        self.last_price = last_price
        self.currency = currency

class MockTicker:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        if self.ticker == 'AAPL':
            self.fast_info = MockFastInfo(175.50, 'USD')
        elif self.ticker == 'MSFT':
            self.fast_info = MockFastInfo(385.00, 'USD')
        elif self.ticker == 'TSLA':
            self.fast_info = MockFastInfo(170.20, 'USD')
        elif self.ticker == 'VOD.L':
            self.fast_info = MockFastInfo(68.40, 'GBp')
        elif self.ticker == 'USDGBP=X':
            self.fast_info = MockFastInfo(0.78, 'GBP')
        elif self.ticker == 'GBPUSD=X':
            self.fast_info = MockFastInfo(1.28, 'USD')
        elif self.ticker == 'INVALIDXYZ':
            self.fast_info = MockFastInfo(None, 'USD')
        else:
            self.fast_info = MockFastInfo(100.0, 'USD')

    def history(self, *args, **kwargs):
        import pandas as pd
        if self.ticker == 'INVALIDXYZ':
            return pd.DataFrame()
        dates = pd.date_range(end='2026-05-22', periods=30)
        prices = [100.0 + i for i in range(30)]
        df = pd.DataFrame({'Close': prices}, index=dates)
        return df

def test_full_user_workflow(client, db):
    with patch("yfinance.Ticker", side_effect=MockTicker):
        # signup
        reg_response = client.post('/register', data={
            'username': 'newuser',
            'email': 'new@financeapp.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'base_currency': 'GBP'
        }, follow_redirects=True)
        assert reg_response.status_code == 200
        assert b"Account created successfully!" in reg_response.data

        # login
        login_response = client.post('/login', data={
            'email': 'new@financeapp.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert login_response.status_code == 200
        assert b"Welcome back" in login_response.data

        # logout
        logout_response = client.post('/logout', follow_redirects=True)
        assert logout_response.status_code == 200
        assert b"You have been logged out successfully." in logout_response.data

        # seed demouser
        with db.session.no_autoflush:
            demo_user = User(
                username="demouser",
                email="demo@financeapp.com",
                base_currency="GBP"
            )
            demo_user.set_password("password123")
            db.session.add(demo_user)
            db.session.commit()

            budgets = [
                Budget(user_id=demo_user.id, category="Groceries", monthly_limit=300.00),
                Budget(user_id=demo_user.id, category="Entertainment", monthly_limit=150.00),
                Budget(user_id=demo_user.id, category="Transport", monthly_limit=120.00),
                Budget(user_id=demo_user.id, category="Bills", monthly_limit=600.00)
            ]
            db.session.add_all(budgets)

            holdings = [
                StockHolding(user_id=demo_user.id, ticker="AAPL", shares=10.0, purchase_price=175.50),
                StockHolding(user_id=demo_user.id, ticker="MSFT", shares=8.0, purchase_price=385.00),
                StockHolding(user_id=demo_user.id, ticker="TSLA", shares=15.0, purchase_price=170.20),
                StockHolding(user_id=demo_user.id, ticker="VOD.L", shares=500.0, purchase_price=0.6840)
            ]
            db.session.add_all(holdings)
            db.session.commit()

        login_demo = client.post('/login', data={
            'email': 'demo@financeapp.com',
            'password': 'password123'
        }, follow_redirects=True)
        assert login_demo.status_code == 200
        assert b"Welcome back, demouser!" in login_demo.data

        # dashboard check
        dashboard_response = client.get('/dashboard')
        assert dashboard_response.status_code == 200
        assert b"id=\"spendingChart\"" in dashboard_response.data
        assert b"id=\"trendChart\"" in dashboard_response.data

        # transactions view
        tx_page_response = client.get('/transactions/')
        assert tx_page_response.status_code == 200
        assert b"Import Bank Statement (CSV)" in tx_page_response.data

        # test csv upload
        csv_content = (
            "Date,Amount,Merchant,Category,Notes\n"
            "2026-05-20,-15.20,Sainsbury's Grocery,Groceries,Weekly shop\n"
            "2026-05-21,-5.50,Transport for London,Transport,Tube ride\n"
            "2026-05-22,3200.00,TechCorp Salary,Salary,Monthly wage\n"
            "2026-05-22,-45.00,Netflix Subscription,Entertainment,Streaming\n"
            "2026-05-22,-120.00,British Gas,Bills,Heating\n"
        )
        csv_file = (io.BytesIO(csv_content.encode('utf-8')), 'test_statement.csv')
        upload_response = client.post('/transactions/upload-scan', data={
            'csv_file': csv_file
        }, content_type='multipart/form-data', follow_redirects=True)
        assert upload_response.status_code == 200
        assert b"Select Mapping Columns" in upload_response.data

        # mapping post
        import re
        html_map_data = upload_response.data.decode('utf-8')
        csv_b64_search = re.search(r'name="csv_b64"\s+value="([^"]+)"', html_map_data)
        assert csv_b64_search is not None
        csv_b64_val = csv_b64_search.group(1)

        preview_response = client.post('/transactions/upload-preview', data={
            'csv_b64': csv_b64_val,
            'map_date': 'Date',
            'map_amount': 'Amount',
            'map_description': 'Merchant',
            'map_category': 'Category',
            'map_notes': 'Notes'
        }, follow_redirects=True)
        assert preview_response.status_code == 200
        assert b"Confirm Bulk Import" in preview_response.data
        assert b"Sainsbury" in preview_response.data
        assert b"Transport for London" in preview_response.data
        assert b"Netflix" in preview_response.data

        # extract json from preview page
        html_data = preview_response.data.decode('utf-8')
        json_search = re.search(r'name="transactions_json"[^>]*value=\'([^\']*)\'', html_data)
        if not json_search:
            json_search = re.search(r'name="transactions_json"[^>]*value="([^"]*)"', html_data)
        
        assert json_search is not None
        import html
        json_str = html.unescape(json_search.group(1))
        
        # confirm import
        confirm_response = client.post('/transactions/upload-confirm', data={
            'transactions_json': json_str
        }, follow_redirects=True)
        
        assert confirm_response.status_code == 200
        assert b"Successfully imported 5 bank statement transactions" in confirm_response.data

        imported_txs = Transaction.query.filter_by(user_id=demo_user.id).all()
        assert len(imported_txs) == 5

        # manual tx budget warning test
        add_tx_response = client.post('/transactions/add', data={
            'date': '2026-05-22',
            'amount': 350.00,
            'description': 'Huge Grocery Haul',
            'category': 'Groceries',
            'type': 'expense',
            'currency': 'GBP',
            'notes': 'Exceeds budget'
        }, follow_redirects=True)
        assert add_tx_response.status_code == 200
        assert b"Transaction added successfully!" in add_tx_response.data

        budget_status_response = client.get('/api/budget-status')
        assert budget_status_response.status_code == 200
        status_data = json.loads(budget_status_response.data.decode('utf-8'))
        
        groceries_budget = next(b for b in status_data['budgets'] if b['category'] == 'Groceries')
        assert groceries_budget['spent'] == 365.20
        assert groceries_budget['over'] is True

        # stocks page values verification
        stocks_response = client.get('/stocks/')
        assert stocks_response.status_code == 200
        assert b"AAPL" in stocks_response.data
        assert b"MSFT" in stocks_response.data
        assert b"TSLA" in stocks_response.data
        assert b"VOD.L" in stocks_response.data
        assert b"342.00" in stocks_response.data

        # invalid ticker gracefully rejected
        add_invalid_stock = client.post('/stocks/add', data={
            'ticker': 'INVALIDXYZ',
            'shares': 10,
            'purchase_price': 100
        }, follow_redirects=True)
        assert add_invalid_stock.status_code == 200
        assert b"Invalid stock ticker symbol" in add_invalid_stock.data

        # end with logout
        logout_response = client.post('/logout', follow_redirects=True)
        assert logout_response.status_code == 200
        assert b"You have been logged out successfully." in logout_response.data
