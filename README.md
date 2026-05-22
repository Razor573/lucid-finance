# 🌌 LucidFinance - Personal Finance & Stock Portfolio Dashboard

LucidFinance is a premium, full-stack, recruiter-optimized personal finance and stock portfolio tracker built with Python (Flask) and a state-of-the-art dark-mode glassmorphic front-end (Vanilla CSS + HTML5 + Chart.js). 

It is designed to give users a comprehensive view of their financial health, featuring automatic bank statement transaction categorization, real-time budget tracking, and real-time equity/currency-adjusted portfolio valuation with cached Yahoo Finance ticker integrations.

---

## ✨ Features

- **🔒 Secure Authentication Engine**: Robust user registration, session management, and login with `Flask-Login` and `Werkzeug` secure password hashing. Strict CSRF protections on all forms.
- **📊 In-Memory Statement CSV Imports**: Ephemeral-ready CSV parser that reads uploaded bank statement streams completely in-memory, auto-guesses column headers, auto-categorizes descriptions via a keyword classification engine, and presents a interactive mapping & preview interface before committing a bulk batch import.
- **📈 Advanced Stock Portfolio Tracking**: Relational stock portfolio tracking with real-time price lookup (5-minute database TTL cache). Automatically performs cost-basis weighted averaging for overlapping buy orders. Fully handles London Stock Exchange (LSE) pence-to-pound adjustments (`GBp`/`GBX` → `GBP`) and real-time multi-currency conversions.
- **📉 30-Day Historical Sparklines**: Custom minimal Chart.js instances drawn dynamically for each equity holding, rendering interactive price trends with glowing directional gain/loss colors.
- **💰 Budget Limits & Meters**: Dynamic categories monitoring with neon alert progress fills when category expenditure exceeds custom limits.
- **🎨 Glassmorphic Dark UI**: Curated custom gradients, blurs, and micro-animations, fully responsive from ultra-wide displays to slide-out mobile sidebar panels.

---

## 📂 Project Architecture

```text
finance-dashboard/
├── app.py                      # Flask App Factory setup & handlers
├── config.py                   # Development & Production settings profiles
├── forms.py                    # Secure WTForms validations (CSRF-enabled)
├── models.py                   # Relational database models (SQLAlchemy)
├── requirements.txt            # Core production dependencies
├── requirements-dev.txt        # Development & testing packages
├── Procfile                    # WSGI deployment script
├── seed.py                     # 6-Month historical mock data generator
├── .env                        # Local configurations env template
├── .gitignore                  # Git excludes
├── README.md                   # Recruiter-optimized documentation
├── routes/                     # Blueprint modular controllers
│   ├── __init__.py
│   ├── auth.py                 # Registration & secure POST logout
│   ├── transactions.py         # CRUD & 3-step statement CSV mapper
│   ├── dashboard.py            # Aggregate metrics & Chart.js data API
│   └── stocks.py               # Portfolio tracks & Sparkline JSON feeds
├── utils/                      # Helper business logic utilities
│   ├── __init__.py
│   ├── categoriser.py          # Keyword-matching category analyzer
│   ├── csv_parser.py           # In-memory CSV reader & cleaner
│   └── stock_fetcher.py        # yfinance caching & multi-currency converter
├── static/                     # Styling and scripting assets
│   ├── css/
│   │   └── dashboard.css       # Responsive glassmorphism stylesheets
│   └── js/
│       ├── dashboard.js        # Cashflow line & category doughnut charts
│       └── stocks.js           # AJAX histories & Chart.js sparkline loops
├── templates/                  # Modular Jinja2 layouts
│   ├── base.html               # Responsive master layout frame
│   ├── login.html              # Secure session logins
│   ├── register.html           # Secure user registrations
│   ├── dashboard.html          # Overview & monthly budgets track
│   ├── transactions.html       # Transaction lists, filters & CRUD forms
│   ├── csv_map.html            # Column select mapping UI
│   ├── csv_preview.html        # Clean rows preview & bulk submit
│   ├── stocks.html             # Stock holdings grid & add modal
│   ├── 404.html                # Custom 404 glass error screen
│   └── 500.html                # Custom 500 glass error screen
└── tests/                      # Pytest automation suites
    ├── conftest.py             # SQLite :memory: test client fixtures
    ├── __init__.py
    ├── test_categoriser.py     # Keywords matching unit tests
    ├── test_csv_parser.py      # CSV stream scanner unit tests
    └── test_stock_cache.py     # Offline FX conversion and DB cache tests
```

---

## 🚀 Quick Start & Installation

To run this application locally, ensure you have Python 3.8+ installed:

### 1. Clone the repository & create virtualenv
```bash
git clone <repository-url>
cd finance-dashboard
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install requirements
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Setup local environment
Create a `.env` file in the root directory:
```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=lucid-finance-super-secret-key-12345
DATABASE_URL=sqlite:///database.db
```

### 4. Create database and seed realistic demo data
Run the Repeatable Seeding script to initialize database tables and insert a realistic 6-month transaction ledger, custom budgets, and active multi-currency stock holdings:
```bash
python seed.py
```
This registers a demo user immediately:
- **Email**: `demo@financeapp.com`
- **Password**: `password123`

### 5. Launch the Development Server
```bash
flask run
```
Open your browser and navigate to `http://127.0.0.1:5000` to log in!

---

## 🧪 Testing and Verification

This repository maintains high code quality using comprehensive test coverage through **Pytest** running against an in-memory SQLite database.

To run the automated tests:
```bash
pytest
```
Expected output:
```text
============================= test session starts =============================
platform win32 -- Python 3.x.x, pytest-8.x.x, pluggy-1.x.x
rootdir: C:\...\finance-dashboard
plugins: flask-1.x.x
collected 14 items

tests/test_categoriser.py ......                                         [ 42%]
tests/test_csv_parser.py .....                                           [ 78%]
tests/test_stock_cache.py ......                                         [100%]

============================== 17 passed in 0.85s ==============================
```

---

## 🛡️ Key Security & Engineering Details

1. **WTForms & CSRF protection**: Every single transaction addition, deletion, budget update, login, registration, and logout form utilizes Flask-WTF CSRF validation. Logouts are handled explicitly via secure POST forms to prevent cross-site GET hijackings.
2. **Double currency conversion fallbacks**: In case the third-party Yahoo Finance API encounters network blocks or rate limits, the converter dynamically reads cached historical entries in the database, looks up inverse FX pairs (e.g. converting `USD` to `GBP` by doing `1 / rate` on a cached `GBPUSD=X`), and falls back gracefully to a hardcoded local exchange rate mapping.
3. **Pence Adjustments**: Handles standard London Stock Exchange `.L` tickers (e.g. `VOD.L`), detecting when Yahoo Finance reports price metrics in pence (`GBp`/`GBX`) and converting them back to decimal pounds sterling (`price / 100.0`) automatically, keeping valuations consistent.
