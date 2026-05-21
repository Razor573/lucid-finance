from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from models import StockCache
from utils.stock_fetcher import get_cached_rate, convert_currency

def test_stock_cache_db_interaction(app, db):
    with app.app_context():
        cache_entry = StockCache(
            ticker="TEST_TICKER",
            cached_price=123.45,
            currency="USD",
            last_fetched=datetime.utcnow()
        )
        db.session.add(cache_entry)
        db.session.commit()

        retrieved = db.session.query(StockCache).filter_by(ticker="TEST_TICKER").first()
        assert retrieved is not None
        assert float(retrieved.cached_price) == 123.45
        assert retrieved.currency == "USD"

def test_get_cached_rate_reads_valid_cache(app, db):
    with app.app_context():
        cache_entry = StockCache(
            ticker="AAPL",
            cached_price=175.50,
            currency="USD",
            last_fetched=datetime.utcnow() - timedelta(seconds=10)
        )
        db.session.add(cache_entry)
        db.session.commit()

        price, currency = get_cached_rate("AAPL", db.session)
        assert price == 175.50
        assert currency == "USD"

def test_convert_currency_same_currency(app, db):
    with app.app_context():
        result = convert_currency(100.0, "GBP", "GBP", db.session)
        assert result == 100.0

def test_convert_currency_direct_pair(app, db):
    with app.app_context():
        cache_entry = StockCache(
            ticker="USDGBP=X",
            cached_price=0.78,
            currency="GBP",
            last_fetched=datetime.utcnow() - timedelta(seconds=10)
        )
        db.session.add(cache_entry)
        db.session.commit()

        result = convert_currency(100.0, "USD", "GBP", db.session)
        assert result == 78.0

def test_convert_currency_inverse_pair(app, db):
    with app.app_context():
        inverse_entry = StockCache(
            ticker="JPYUSD=X",
            cached_price=0.0067,
            currency="USD",
            last_fetched=datetime.utcnow() - timedelta(seconds=10)
        )
        db.session.add(inverse_entry)
        db.session.commit()

        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = None
        mock_ticker.history.return_value = MagicMock(empty=True)

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = convert_currency(100.0, "USD", "JPY", db.session)
            expected = 100.0 / 0.0067
            assert abs(result - expected) < 0.01

def test_convert_currency_static_fallback(app, db):
    with app.app_context():
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = None
        mock_ticker.history.return_value = MagicMock(empty=True)

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = convert_currency(100.0, "USD", "GBP", db.session)
            assert result == 78.0

            result2 = convert_currency(100.0, "GBP", "USD", db.session)
            assert result2 == 128.0

def test_get_cached_rate_concurrent_race_condition(app, db):
    with app.app_context():
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 150.0
        mock_ticker.fast_info.currency = "USD"
        
        original_commit = db.session.commit
        call_count = 0
        
        def mock_commit():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from sqlalchemy.exc import IntegrityError
                raise IntegrityError("mock statement", "mock params", Exception("UNIQUE constraint failed: stock_cache.ticker"))
            else:
                original_commit()
                
        original_query = db.session.query
        def mock_query(*args, **kwargs):
            query_obj = original_query(*args, **kwargs)
            if args and args[0] == StockCache:
                original_first = query_obj.first
                def mock_first():
                    if call_count > 0:
                        return StockCache(ticker="RACE_TICKER", cached_price=150.0, currency="USD")
                    return original_first()
                query_obj.first = mock_first
            return query_obj
                
        with patch("yfinance.Ticker", return_value=mock_ticker), \
             patch.object(db.session, "commit", side_effect=mock_commit), \
             patch.object(db.session, "query", side_effect=mock_query):
             
            price, currency = get_cached_rate("RACE_TICKER", db.session)
            assert price == 150.0
            assert currency == "USD"
