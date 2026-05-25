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
        elif self.ticker == 'EURUSD=X':
            self.fast_info = MockFastInfo(1.09, 'USD')
        elif self.ticker == 'USDEUR=X':
            self.fast_info = MockFastInfo(0.92, 'EUR')
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

def test_settings_and_currency_conversion(client, db):
    with patch("yfinance.Ticker", side_effect=MockTicker):
        # register & login a new user
        client.post('/register', data={
            'username': 'currencyuser',
            'email': 'currency@finance.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'base_currency': 'GBP'
        }, follow_redirects=True)
        
        client.post('/login', data={
            'email': 'currency@finance.com',
            'password': 'password123'
        }, follow_redirects=True)

        # 1. Verify we can access the settings page and change base_currency to USD
        settings_get = client.get('/settings')
        assert settings_get.status_code == 200
        assert b"User Profile" in settings_get.data

        settings_post = client.post('/settings', data={
            'username': 'currencyuser',
            'email': 'currency@finance.com',
            'base_currency': 'USD'
        }, follow_redirects=True)
        assert settings_post.status_code == 200
        assert b"Your settings have been updated." in settings_post.data

        user = User.query.filter_by(username='currencyuser').first()
        assert user.base_currency == 'USD'

        # 2. Add some transactions in different currencies
        # Base is USD.
        # Add income: $100.00 USD
        client.post('/transactions/add', data={
            'date': date.today().strftime('%Y-%m-%d'),
            'amount': 100.00,
            'description': 'USD Income',
            'category': 'Salary',
            'type': 'income',
            'currency': 'USD',
            'notes': ''
        }, follow_redirects=True)

        # Add expense: £50.00 GBP (Static rate USD->GBP is 0.78, GBP->USD is 1.28)
        # £50 GBP should convert to 50 * 1.28 = $64.00 USD
        client.post('/transactions/add', data={
            'date': date.today().strftime('%Y-%m-%d'),
            'amount': 50.00,
            'description': 'GBP Expense',
            'category': 'Groceries',
            'type': 'expense',
            'currency': 'GBP',
            'notes': ''
        }, follow_redirects=True)

        # Add expense: €100.00 EUR (Static rate EUR->USD is 1.09)
        # €100 EUR should convert to 100 * 1.09 = $109.00 USD
        client.post('/transactions/add', data={
            'date': date.today().strftime('%Y-%m-%d'),
            'amount': 100.00,
            'description': 'EUR Expense',
            'category': 'Bills',
            'type': 'expense',
            'currency': 'EUR',
            'notes': ''
        }, follow_redirects=True)

        # 3. Verify Dashboard calculations
        # total_income = 100.00 USD
        # total_expenses = 64.00 (GBP) + 109.00 (EUR) = 173.00 USD
        dashboard = client.get('/dashboard')
        assert dashboard.status_code == 200
        assert b"100" in dashboard.data
        assert b"173" in dashboard.data

        # 4. Verify API spending-by-category returns correct base currency sums
        spending_resp = client.get('/api/spending-by-category')
        assert spending_resp.status_code == 200
        spending_data = json.loads(spending_resp.data.decode('utf-8'))
        assert spending_data['currency'] == 'USD'
        assert 'Groceries' in spending_data['labels']
        assert 64.0 in spending_data['data']
        assert 109.0 in spending_data['data']

        # 5. Verify API monthly-trend returns correct trend data
        trend_resp = client.get('/api/monthly-trend')
        assert trend_resp.status_code == 200
        trend_data = json.loads(trend_resp.data.decode('utf-8'))
        assert trend_data['currency'] == 'USD'
        assert trend_data['income'][-1] == 100.0
        assert trend_data['expenses'][-1] == 173.0

        # 6. Verify transactions page renders converted and original amounts
        tx_page = client.get('/transactions/')
        assert tx_page.status_code == 200
        assert b"$64.00" in tx_page.data
        assert b"\xc2\xa350.00" in tx_page.data  # GBP symbol and amount

        # 7. Verify stock history converted successfully using convert_currency
        # VOD.L is in GBp, converted first to GBP (divided by 100), then converted to USD (base)
        history_resp = client.get('/stocks/api/history/VOD.L')
        assert history_resp.status_code == 200
        history_data = json.loads(history_resp.data.decode('utf-8'))
        assert history_data['currency'] == 'USD'
        # Original price for first day is 100, which in GBp is 1 GBP.
        # converted to USD using GBP->USD rate (1.28) is 1.28
        assert history_data['prices'][0] == 1.28

        # 8. Test CSV Export of transactions
        export_resp = client.get('/settings/export/transactions')
        assert export_resp.status_code == 200
        assert export_resp.mimetype == 'text/csv'
        assert b"Date,Amount,Description,Category,Type,Currency,Notes" in export_resp.data
        assert b"USD Income" in export_resp.data
        assert b"GBP Expense" in export_resp.data

        # 9. Test Reset of all data
        reset_resp = client.post('/settings/reset', follow_redirects=True)
        assert reset_resp.status_code == 200
        assert b"All account data has been successfully cleared." in reset_resp.data
        
        # Verify db counts for user are 0
        assert Transaction.query.filter_by(user_id=user.id).count() == 0
        assert Budget.query.filter_by(user_id=user.id).count() == 0
        assert StockHolding.query.filter_by(user_id=user.id).count() == 0

