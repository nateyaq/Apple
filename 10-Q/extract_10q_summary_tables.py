import requests
from bs4 import BeautifulSoup
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

# Example usage:
# Single filing: python3 extract_10q_summary_tables.py --url <10-Q-url> --output <output-file>
# Batch mode (latest N filings): python3 extract_10q_summary_tables.py --last-n 8 --output <output-file>
# Fetch all available 10-Qs: python3 extract_10q_summary_tables.py --all --output <output-file>

CIK = '320193'  # Apple
HEADERS = {'User-Agent': "apple-dashboard@example.com"}
SEC_SUBMISSIONS_URL = f'https://data.sec.gov/submissions/CIK{int(CIK):010d}.json'

# --- Argument Parsing ---
def get_arg_parser():
    parser = argparse.ArgumentParser(description="Apple 10-Q Summary Table Extractor")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--all', action='store_true', help='Fetch all available 10-Qs')
    group.add_argument('--last-n', type=int, default=5, help='Fetch last N 10-Qs (default 5)')
    parser.add_argument('--url', type=str, default=None, help='Specific SEC 10-Q filing URL to process')
    parser.add_argument('--output', type=str, default='10q_summary_data.json', help='Output JSON file')
    return parser

# --- SEC Filing Utilities ---
def get_10q_filing_urls(count=None):
    resp = requests.get(SEC_SUBMISSIONS_URL, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    filings = data['filings']['recent']
    urls = []
    for i, form in enumerate(filings['form']):
        if form == '10-Q':
            accession = filings['accessionNumber'][i].replace('-', '')
            primary_doc = filings['primaryDocument'][i]
            filing_date = filings['filingDate'][i]
            doc_url = f'https://www.sec.gov/Archives/edgar/data/{int(CIK)}/{accession}/{primary_doc}'
            urls.append({'url': doc_url, 'date': filing_date, 'accession': filings['accessionNumber'][i]})
            if count and len(urls) >= count:
                break
    return urls

# --- Table Extraction ---
def find_section_table(soup, keywords):
    # keywords: list of strings to match in section headers
    header_tags = soup.find_all(['b', 'strong', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'], string=True)
    for tag in header_tags:
        header_text = tag.get_text(strip=True).lower()
        if any(kw.lower() in header_text for kw in keywords):
            next_table = tag.find_next('table')
            if next_table:
                return next_table
    return None

def extract_table_data(table):
    rows = []
    for tr in table.find_all('tr'):
        row = []
        for td in tr.find_all(['td', 'th'], recursive=False):
            # Always extract value from <ix:nonfraction> if present
            ix = td.find(['ix:nonfraction', 'ix:nonnumeric'])
            if ix:
                text = ix.get_text(strip=True)
            else:
                text = td.get_text(separator=' ', strip=True)
            text = text.replace('\xa0', '')  # Remove non-breaking spaces
            # Handle colspan
            colspan = int(td.get('colspan', 1))
            if colspan > 1:
                row.extend([text] * colspan)
            else:
                row.append(text)
        if row:
            rows.append(row)
    return rows

# Helper to find the first non-empty header row (with at least 2 columns)
def find_header_row(table_data):
    for i, row in enumerate(table_data):
        if len(row) > 1 and any(str(cell).strip() for cell in row[1:]):
            return i, row
    return 0, table_data[0] if table_data else []

def clean_number(val):
    if isinstance(val, (int, float)):
        return val
    if not isinstance(val, str):
        return None
    # Remove $, commas, parentheses, and % signs
    val = val.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').replace('%', '').strip()
    try:
        return float(val)
    except Exception:
        return None

def clean_label(label):
    # Remove trailing footnote markers like (1), (2), etc. and trailing colons
    label = re.sub(r'[:\s]*$', '', re.sub(r'\s*\([0-9]+\)$', '', label)).strip()
    # Remove all non-alphanumeric characters except spaces
    label = re.sub(r'[^a-zA-Z0-9 ]', '', label)
    label = re.sub(r'\s+', ' ', label)  # Collapse multiple spaces
    return label.strip().lower()

def find_year_value(row, year_cols, idx):
    col_idx, year = year_cols[idx]
    # Look for the value in the next cell after the year
    value_idx = col_idx + 1
    if value_idx < len(row):
        val = row[value_idx]
        # Skip if it's just a '$' sign
        if val == '$':
            value_idx += 1
            if value_idx < len(row):
                val = row[value_idx]
        return clean_number(val)
    return None

def find_percent_change(row, year_cols, idx):
    col_idx, year = year_cols[idx]
    # Look for the percent change in the cell after the value
    change_idx = col_idx + 2
    if change_idx < len(row):
        val = row[change_idx]
        # Handle cases where the percent sign is in a separate cell
        if isinstance(val, str) and '%' in val:
            return clean_number(val)
        elif change_idx + 1 < len(row) and row[change_idx + 1] == '%':
            return clean_number(val)
    return None

def is_year(val):
    try:
        year = int(str(val).strip())
        return 2000 <= year <= 2100
    except Exception:
        return False

def is_numeric(val):
    if val is None:
        return False
    val = str(val).replace(',', '').replace('$', '').strip()
    return re.match(r'^-?\d+(\.\d+)?$', val) is not None

def is_percent(val):
    if val is None:
        return False
    val = str(val).replace('%', '').replace('(', '-').replace(')', '').strip()
    return re.match(r'^-?\d+(\.\d+)?$', val) is not None

def clean_numeric(val):
    if val is None:
        return None
    val = str(val).replace(',', '').replace('$', '').strip()
    try:
        return float(val)
    except Exception:
        return None

def clean_percent(val):
    if val is None:
        return None
    val = str(val).replace('%', '').replace('(', '-').replace(')', '').strip()
    try:
        return float(val)
    except Exception:
        return None

def get_year_col_map(header):
    # Returns a list of dicts: [{'year': 2023, 'year_idx': i, 'change_idx': j}, ...]
    year_col_map = []
    for i, col in enumerate(header):
        if is_year(col):
            year = int(col)
            # Find the next 'Change' column after the year
            change_idx = None
            for j in range(i+1, len(header)):
                if isinstance(header[j], str) and 'change' in header[j].lower():
                    change_idx = j
                    break
                if is_year(header[j]):
                    break
            year_col_map.append({'year': year, 'year_idx': i, 'change_idx': change_idx})
    return year_col_map

def find_valid_numeric(row, start_idx):
    # Find the next valid numeric value in the row after start_idx
    for i in range(start_idx+1, len(row)):
        val = row[i]
        if is_numeric(val):
            return i, clean_numeric(val)
    return None, None

def find_valid_percent(row, change_idx):
    if change_idx is not None and change_idx < len(row):
        val = row[change_idx]
        if is_percent(val):
            return clean_percent(val)
    return None

def tidy_products_services_table(table_data):
    # Debug: print the full table_data for investigation
    print('[DEBUG] Full revenue table_data:')
    for row in table_data:
        print(row)
    if not table_data or len(table_data) < 3:
        return []
    # Find the header rows: period type and date
    period_row_idx = None
    date_row_idx = None
    for i, row in enumerate(table_data):
        if any("three months ended" in str(cell).lower() or "six months ended" in str(cell).lower() for cell in row):
            period_row_idx = i
            date_row_idx = i + 1
            break
    if period_row_idx is None or date_row_idx is None:
        return []
    period_row = table_data[period_row_idx]
    date_row = table_data[date_row_idx]
    # Build a column-to-period mapping
    period_labels = []
    last_period = ''
    for p, d in zip(period_row, date_row):
        label = p.strip()
        if label:
            last_period = label
        date = d.strip()
        if date:
            period_labels.append(f"{last_period} {date}")
        else:
            period_labels.append(last_period)
    # Extend period_labels to match the max row length
    max_row_len = max(len(row) for row in table_data)
    if len(period_labels) < max_row_len:
        period_labels += [period_labels[-1]] * (max_row_len - len(period_labels))
    # Extract product rows
    products = []
    for row in table_data[date_row_idx + 1:]:
        if not row or not row[0]:
            continue
        product = row[0].strip()
        if not product or product.lower() == "total net sales":
            continue
        # Extract numeric values and their column indices
        for i, cell in enumerate(row):
            if cell and cell.replace(",", "").replace("$", "").strip().replace(".", "").isdigit():
                value = float(cell.replace(",", "").replace("$", ""))
                period = period_labels[i] if i < len(period_labels) else ''
                if period:
                    products.append({
                        "product": product,
                        "period": period,
                        "net_sales": value,
                        "type": "product" if product.lower() != "total net sales" else "total"
                    })
    return products

def tidy_segment_operating_table(table_data):
    if not table_data or len(table_data) < 3:
        return []
    # Find the header rows: period type and date
    period_row_idx = None
    date_row_idx = None
    for i, row in enumerate(table_data):
        if any("three months ended" in str(cell).lower() or "six months ended" in str(cell).lower() for cell in row):
            period_row_idx = i
            date_row_idx = i + 1
            break
    if period_row_idx is None or date_row_idx is None:
        return []
    period_row = table_data[period_row_idx]
    date_row = table_data[date_row_idx]
    # Build period labels for each column
    period_labels = []
    last_period = ''
    for p, d in zip(period_row, date_row):
        label = p.strip()
        if label:
            last_period = label
        date = d.strip()
        if date:
            period_labels.append(f"{last_period} {date}")
        else:
            period_labels.append(last_period)
    max_row_len = max(len(row) for row in table_data)
    if len(period_labels) < max_row_len:
        period_labels += [period_labels[-1]] * (max_row_len - len(period_labels))
    # Acceptable region names (substring match)
    valid_regions = [
        "americas",
        "europe",
        "greater china",
        "japan",
        "rest of asia pacific"
    ]
    tidy_rows = []
    current_region = None
    for row in table_data[date_row_idx+1:]:
        print('[DEBUG] Row:', row)
        if not row or not isinstance(row[0], str):
            continue
        label = clean_label(row[0].strip())
        print('[DEBUG] Cleaned label:', label)
        if not label:
            continue
        # Check for region header
        if any(region in label for region in valid_regions):
            current_region = row[0].strip()
            print('[DEBUG] Set current_region:', current_region)
            continue
        # Only extract 'Net sales' sub-rows for regions
        if current_region and label == "net sales":
            print('[DEBUG] Extracting net sales for region:', current_region)
            for i, val in enumerate(row):
                if is_numeric(val):
                    period = period_labels[i] if i < len(period_labels) else ''
                    num = clean_number(val)
                    if num is not None:
                        tidy_rows.append({
                            "type": "region",
                            "region": current_region,
                            "period": period,
                            "net_sales": num
                        })
    return tidy_rows

def find_relevant_tables(soup, keywords):
    relevant_tables = []
    # Search for all ix:continuation, ix:nonnumeric, divs that contain a table
    for container in soup.find_all(['ix:continuation', 'ix:nonnumeric', 'div']):
        text = container.get_text(separator=' ', strip=True).lower()
        if any(kw.lower() in text for kw in keywords):
            for table in container.find_all('table'):
                # Only add tables that contain a product keyword (e.g., 'iphone')
                table_text = table.get_text(separator=' ', strip=True).lower()
                if any(prod in table_text for prod in ['iphone', 'mac', 'ipad', 'wearables', 'disaggregated net sales']):
                    relevant_tables.append(table)
    return relevant_tables

# --- Main Extraction Logic ---
def extract_10q_summary(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    revenue_tables = find_relevant_tables(soup, ['disaggregated net sales', 'net sales', 'revenue'])
    segment_tables = find_relevant_tables(soup, [
        'segment information and geographic data',
        'segment',
        'geographic',
        'operating performance'
    ])
    prod_data = []
    seg_data = []
    if revenue_tables:
        revenue_rows = extract_table_data(revenue_tables[0])
        print("[DEBUG] Revenue table rows:")
        for row in revenue_rows:
            print(row)
        prod_data = tidy_products_services_table(revenue_rows)
    if segment_tables:
        segment_rows = extract_table_data(segment_tables[0])
        print("[DEBUG] Segment table rows:", segment_rows)
        seg_data = tidy_segment_operating_table(segment_rows)
    return {'url': url, 'products_and_services': prod_data, 'segment_operating': seg_data}

# --- Main Entrypoint ---
def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    filings = []
    if args.url:
        filings = [{'url': args.url}]
    elif args.all:
        filings = get_10q_filing_urls()
    else:
        filings = get_10q_filing_urls(count=args.last_n)
    results = []
    for filing in filings:
        print(f"Extracting: {filing['url']}")
        try:
            summary = extract_10q_summary(filing['url'])
            summary['date'] = filing.get('date')
            summary['accession'] = filing.get('accession')
            results.append(summary)
        except Exception as e:
            print(f"Error extracting {filing['url']}: {e}")
    # Write output
    out_path = Path(__file__).parent / args.output
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} filings to {out_path}")

def extract_revenue_table(table):
    """Extract revenue data from the table."""
    revenue_data = {
        'Products': {},
        'Services': {},
        'Total net sales': {}
    }
    
    # Track if we're in a Products section
    in_products_section = False
    current_product = None
    
    # First pass: identify all valid labels
    valid_labels = set()
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            if label:
                valid_labels.add(label)
    
    print("\nCandidate labels from revenue table:")
    for label in sorted(valid_labels):
        print(f"  - {label}")
    
    # Second pass: extract data
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            if not label:
                continue
                
            # Check if this is a Products section header
            if label == 'Products':
                in_products_section = True
                continue
                
            # If we're in Products section, handle sub-rows
            if in_products_section:
                if label in ['iPhone', 'Mac', 'iPad', 'Wearables, Home and Accessories']:
                    current_product = label
                    revenue_data['Products'][current_product] = {}
                    for i, cell in enumerate(cells[1:], 1):
                        value = cell.get_text(strip=True)
                        if value:
                            revenue_data['Products'][current_product][f'Q{i}'] = value
                elif label == 'Services':
                    in_products_section = False
                    current_product = None
                elif current_product and label == 'Total net sales':
                    in_products_section = False
                    current_product = None
                    
            # Handle main categories
            if label in ['Services', 'Total net sales']:
                for i, cell in enumerate(cells[1:], 1):
                    value = cell.get_text(strip=True)
                    if value:
                        revenue_data[label][f'Q{i}'] = value
    
    return revenue_data

if __name__ == '__main__':
    main() 