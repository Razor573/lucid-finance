from utils.categoriser import categorise

def test_categorise_salary():
    assert categorise("Monthly Salary payment") == "Salary"
    assert categorise("WAGES FOR MAY") == "Salary"
    assert categorise("STRIPE TRANSFER PAYOUT") == "Salary"

def test_categorise_groceries():
    assert categorise("Tesco Stores 1234") == "Groceries"
    assert categorise("SAINSBURY'S S/MKT") == "Groceries"
    assert categorise("Waitrose grocery delivery") == "Groceries"

def test_categorise_transport():
    assert categorise("Uber Trip Friday") == "Transport"
    assert categorise("TfL contactless tube charge") == "Transport"
    assert categorise("Shell petrol station") == "Transport"

def test_categorise_entertainment():
    assert categorise("Netflix subscription renewal") == "Entertainment"
    assert categorise("Spotify Premium Music") == "Entertainment"
    assert categorise("Starbucks Coffee London") == "Entertainment"

def test_categorise_bills():
    assert categorise("British Gas energy DD") == "Bills"
    assert categorise("Council Tax monthly bill") == "Bills"
    assert categorise("EE Mobile phone payment") == "Bills"

def test_categorise_other_fallback():
    assert categorise("Unrecognized payment to unknown") == "Other"
    assert categorise("Random store purchase") == "Other"
    assert categorise("") == "Other"
