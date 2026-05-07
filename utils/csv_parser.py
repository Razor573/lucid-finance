import pandas as pd
from datetime import datetime
from utils.categoriser import categorise

def scan_csv_headers(file_stream):
    try:
        file_stream.seek(0)
        df = pd.read_csv(file_stream, nrows=5)
        return list(df.columns), None
    except Exception as e:
        return [], f"Failed to parse CSV headers: {str(e)}"

def parse_mapped_csv(file_stream, mapping, base_currency='GBP'):
    try:
        file_stream.seek(0)
        df = pd.read_csv(file_stream)
        df = df.fillna('')
        
        rows = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # parse date
                date_str = str(row[mapping['date']]).strip()
                parsed_date = None
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S'):
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                        
                if parsed_date is None:
                    try:
                        parsed_date = pd.to_datetime(date_str).date()
                    except Exception:
                        pass
                        
                if parsed_date is None:
                    errors.append(f"Row {idx + 1}: Invalid date format '{date_str}'. Expected YYYY-MM-DD or DD/MM/YYYY.")
                    continue
                
                # parse amount
                amt_str = str(row[mapping['amount']]).strip()
                for ch in ['$', '£', '€', ',', ' ']:
                    amt_str = amt_str.replace(ch, '')
                try:
                    amount = float(amt_str)
                except ValueError:
                    errors.append(f"Row {idx + 1}: Invalid numeric amount '{amt_str}'.")
                    continue
                
                # parse description
                desc = str(row[mapping['description']]).strip()
                if not desc:
                    desc = "Unnamed Transaction"
                
                # notes (optional)
                notes = ""
                if mapping.get('notes') and mapping['notes'] in row:
                    notes = str(row[mapping['notes']]).strip()
                
                # type (optional)
                tx_type = 'expense'
                if mapping.get('type') and mapping['type'] in row:
                    raw_type = str(row[mapping['type']]).strip().lower()
                    if raw_type in ['income', 'credit', 'in', 'deposit', 'receive', 'salary', 'cr']:
                        tx_type = 'income'
                    elif raw_type in ['expense', 'debit', 'out', 'withdrawal', 'pay', 'dr']:
                        tx_type = 'expense'
                    else:
                        tx_type = 'income' if amount > 0 else 'expense'
                else:
                    tx_type = 'income' if amount > 0 else 'expense'
                
                abs_amount = abs(amount)
                
                # category (optional)
                cat = ""
                if mapping.get('category') and mapping['category'] in row:
                    cat = str(row[mapping['category']]).strip()
                
                if not cat or cat.lower() == 'other':
                    cat = categorise(desc)
                    
                rows.append({
                    'date': parsed_date,
                    'amount': abs_amount,
                    'description': desc[:255],
                    'category': cat[:100],
                    'type': tx_type,
                    'currency': base_currency,
                    'notes': notes[:255] if notes else None
                })
            except Exception as e:
                errors.append(f"Row {idx + 1}: Processing error: {str(e)}")
                
        return rows, errors
    except Exception as e:
        return [], [f"Failed to read CSV rows: {str(e)}"]
