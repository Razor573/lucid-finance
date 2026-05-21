import io
import re
import pytest
from datetime import date
from models import User, Transaction, Budget, StockHolding
from utils.rate_limiter import reset_rate_limits

@pytest.fixture(autouse=True)
def clean_rate_limits():
    reset_rate_limits()

def test_security_headers_present(client):
    res = client.get('/')
    assert res.status_code in [200, 302]
    assert res.headers.get('X-Frame-Options') == 'DENY'
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert res.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert 'Content-Security-Policy' in res.headers
    assert 'Permissions-Policy' in res.headers

def test_hsts_in_production(client, monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    res = client.get('/')
    assert res.headers.get('Strict-Transport-Security') == 'max-age=31536000; includeSubDomains'

def test_cache_control_for_authenticated_users(client, db):
    user = User(username='cacheuser', email='cache@test.com', base_currency='GBP')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    
    # anonymous
    res_anon = client.get('/login')
    assert 'no-store' not in res_anon.headers.get('Cache-Control', '')
    
    # log in
    login_res = client.post('/login', data={'email': 'cache@test.com', 'password': 'password123'}, follow_redirects=True)
    assert login_res.status_code == 200
    
    # authenticated
    res_auth = client.get('/dashboard')
    assert res_auth.status_code == 200
    assert 'no-store' in res_auth.headers.get('Cache-Control', '')
    assert 'private' in res_auth.headers.get('Cache-Control', '')
    assert res_auth.headers.get('Pragma') == 'no-cache'
    assert 'Cookie' in res_auth.headers.get('Vary', '')

def test_unauthorized_access_blocked(client):
    protected_routes = ['/dashboard', '/transactions/', '/stocks/']
    for route in protected_routes:
        res = client.get(route)
        assert res.status_code == 302
        assert '/login' in res.headers.get('Location', '')

def test_idor_cross_user_access_blocked(client, db):
    user_a = User(username='usera', email='usera@test.com')
    user_a.set_password('password123')
    user_b = User(username='userb', email='userb@test.com')
    user_b.set_password('password123')
    db.session.add_all([user_a, user_b])
    db.session.commit()
    
    tx_b = Transaction(user_id=user_b.id, date=date.today(), amount=100.0, description="Secret B", category="Groceries", type="expense")
    budget_b = Budget(user_id=user_b.id, category="Transport", monthly_limit=50.0)
    stock_b = StockHolding(user_id=user_b.id, ticker="AAPL", shares=10, purchase_price=150)
    db.session.add_all([tx_b, budget_b, stock_b])
    db.session.commit()
    
    client.post('/login', data={'email': 'usera@test.com', 'password': 'password123'}, follow_redirects=True)
    
    res_edit_tx = client.post(f'/transactions/edit/{tx_b.id}', data={
        'date': '2026-05-22',
        'amount': 200.0,
        'description': 'Hacked',
        'category': 'Groceries',
        'type': 'expense',
        'currency': 'GBP'
    })
    assert res_edit_tx.status_code == 404
    
    res_delete_tx = client.post(f'/transactions/delete/{tx_b.id}')
    assert res_delete_tx.status_code == 404
    
    res_delete_budget = client.post(f'/dashboard/budget/delete/{budget_b.id}')
    assert res_delete_budget.status_code == 404
    
    res_delete_stock = client.post(f'/stocks/delete/{stock_b.id}')
    assert res_delete_stock.status_code == 404

def test_csrf_protection_enforced(app, db):
    app.config['WTF_CSRF_ENABLED'] = True
    client = app.test_client()
    
    user = User(username='csrfuser', email='csrf@test.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    
    res = client.post('/login', data={'email': 'csrf@test.com', 'password': 'password123'})
    assert res.status_code == 400
    assert b"CSRF" in res.data

def test_login_rate_limiting(app, db):
    app.config['TEST_RATE_LIMITING'] = True
    client = app.test_client()
    
    for i in range(5):
        client.post('/login', data={'email': 'rate@test.com', 'password': 'wrongpassword'})
        
    res = client.post('/login', data={'email': 'rate@test.com', 'password': 'wrongpassword'})
    assert res.status_code == 429
    assert b"Too many requests" in res.data

def test_malformed_csv_rejected_safely(client, db):
    user = User(username='csvuser', email='csv@test.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'email': 'csv@test.com', 'password': 'password123'}, follow_redirects=True)
    
    csv_content = ""
    csv_file = (io.BytesIO(csv_content.encode('utf-8')), 'bad.csv')
    res = client.post('/transactions/upload-scan', data={'csv_file': csv_file}, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b"Failed to parse CSV headers" in res.data or b"Please upload a valid CSV file" in res.data
