import io
from datetime import date
from utils.csv_parser import scan_csv_headers, parse_mapped_csv

def test_scan_csv_headers_success():
    csv_data = "Transaction Date,Value,Payee,Notes\n2026-05-22,-15.50,Tesco Store,weekly shop\n"
    stream = io.StringIO(csv_data)
    headers, err = scan_csv_headers(stream)
    
    assert err is None
    assert headers == ["Transaction Date", "Value", "Payee", "Notes"]

def test_scan_csv_headers_failure():
    # Empty string or bad CSV format
    stream = io.StringIO("")
    headers, err = scan_csv_headers(stream)
    assert err is not None
    assert headers == []

def test_parse_mapped_csv_success():
    csv_data = (
        "Date,Amount,Description,Category,Type,Reference\n"
        "2026-05-20,45.20,EE Mobile,Bills,expense,monthly plan\n"
        "21/05/2026,-15.00,Tesco,Groceries,expense,food shop\n"
        "2026-05-22,3200.00,Wages,Salary,income,payroll payout\n"
    )
    stream = io.StringIO(csv_data)
    mapping = {
        'date': 'Date',
        'amount': 'Amount',
        'description': 'Description',
        'category': 'Category',
        'type': 'Type',
        'notes': 'Reference'
    }
    
    parsed, errors = parse_mapped_csv(stream, mapping, base_currency='GBP')
    
    assert len(errors) == 0
    assert len(parsed) == 3
    
    # Check row 1
    assert parsed[0]['date'] == date(2026, 5, 20)
    assert parsed[0]['amount'] == 45.20
    assert parsed[0]['description'] == "EE Mobile"
    assert parsed[0]['category'] == "Bills"
    assert parsed[0]['type'] == "expense"
    assert parsed[0]['notes'] == "monthly plan"
    assert parsed[0]['currency'] == "GBP"

    # Check row 2 (Pence format / negative signs)
    assert parsed[1]['date'] == date(2026, 5, 21)
    assert parsed[1]['amount'] == 15.00  # Normalized to positive absolute value
    assert parsed[1]['description'] == "Tesco"
    assert parsed[1]['category'] == "Groceries"
    assert parsed[1]['type'] == "expense"

    # Check row 3
    assert parsed[2]['date'] == date(2026, 5, 22)
    assert parsed[2]['amount'] == 3200.00
    assert parsed[2]['description'] == "Wages"
    assert parsed[2]['category'] == "Salary"
    assert parsed[2]['type'] == "income"

def test_parse_mapped_csv_with_errors():
    csv_data = (
        "Date,Amount,Description\n"
        "invalid-date,10.00,Coffee\n"
        "2026-05-20,bad-amount,Gas\n"
        "2026-05-21,12.50,Sainsburys\n"
    )
    stream = io.StringIO(csv_data)
    mapping = {
        'date': 'Date',
        'amount': 'Amount',
        'description': 'Description'
    }
    
    parsed, errors = parse_mapped_csv(stream, mapping, base_currency='USD')
    
    assert len(errors) == 2
    assert "Invalid date format" in errors[0]
    assert "Invalid numeric amount" in errors[1]
    
    assert len(parsed) == 1
    assert parsed[0]['date'] == date(2026, 5, 21)
    assert parsed[0]['amount'] == 12.50
    assert parsed[0]['description'] == "Sainsburys"
    assert parsed[0]['category'] == "Groceries"  # Auto-categorized
    assert parsed[0]['currency'] == "USD"
