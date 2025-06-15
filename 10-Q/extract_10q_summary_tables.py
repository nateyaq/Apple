import requests
from bs4 import BeautifulSoup
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

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
            # Get text and clean it
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
    # Remove trailing footnote markers like (1), (2), etc.
    return re.sub(r'\s*\([0-9]+\)$', '', label).strip()

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
    if not table_data or len(table_data) < 2:
        return []
    
    # Find header row with years
    header_idx, header = find_header_row(table_data)
    year_cols = [(i, int(col)) for i, col in enumerate(header) if is_year(col)]
    
    tidy_rows = []
    products = set()
    
    # First pass: collect all product names
    for row in table_data[header_idx+1:]:
        if not row or not isinstance(row[0], str):
            continue
        label = clean_label(row[0].strip())
        if not label:
            continue
        if label.lower().startswith('total'):
            products.add(('total', label))
        else:
            products.add(('product', label))
    
    # Second pass: extract data for each product
    for row_type, label in products:
        for idx, (col_idx, year) in enumerate(year_cols):
            found_row = None
            for row in table_data[header_idx+1:]:
                if not row or not isinstance(row[0], str):
                    continue
                if clean_label(row[0].strip()) == label:
                    found_row = row
                    break
            
            if found_row:
                net_sales = find_year_value(found_row, year_cols, idx)
                percent_change = find_percent_change(found_row, year_cols, idx)
                
                # Only create record if we have net sales data
                if net_sales is not None:
                    record = {
                        "type": row_type,
                        "product": label,
                        "year": year,
                        "net_sales": net_sales
                    }
                    
                    if percent_change is not None:
                        record["percent_change"] = percent_change
                    
                    # Add previous year data if available
                    if idx + 1 < len(year_cols):
                        prev_year = year_cols[idx + 1][1]
                        prev_net_sales = find_year_value(found_row, year_cols, idx + 1)
                        if prev_net_sales is not None:
                            record.update({
                                "previous_year": prev_year,
                                "previous_year_net_sales": prev_net_sales
                            })
                    
                    tidy_rows.append(record)
    
    return tidy_rows

def tidy_segment_operating_table(table_data):
    if not table_data or len(table_data) < 2:
        return []
    
    # Find header row with years
    header_idx, header = find_header_row(table_data)
    year_cols = [(i, int(col)) for i, col in enumerate(header) if is_year(col)]
    
    tidy_rows = []
    regions = set()
    
    # First pass: collect all region names
    for row in table_data[header_idx+1:]:
        if not row or not isinstance(row[0], str):
            continue
        label = clean_label(row[0].strip())
        if not label:
            continue
        if label.lower().startswith('total'):
            regions.add(('total', label))
        else:
            regions.add(('region', label))
    
    # Second pass: extract data for each region
    for row_type, label in regions:
        for idx, (col_idx, year) in enumerate(year_cols):
            found_row = None
            for row in table_data[header_idx+1:]:
                if not row or not isinstance(row[0], str):
                    continue
                if clean_label(row[0].strip()) == label:
                    found_row = row
                    break
            
            if found_row:
                net_sales = find_year_value(found_row, year_cols, idx)
                percent_change = find_percent_change(found_row, year_cols, idx)
                
                # Only create record if we have net sales data
                if net_sales is not None:
                    record = {
                        "type": row_type,
                        "region": label,
                        "year": year,
                        "net_sales": net_sales
                    }
                    
                    if percent_change is not None:
                        record["percent_change"] = percent_change
                    
                    # Add previous year data if available
                    if idx + 1 < len(year_cols):
                        prev_year = year_cols[idx + 1][1]
                        prev_net_sales = find_year_value(found_row, year_cols, idx + 1)
                        if prev_net_sales is not None:
                            record.update({
                                "previous_year": prev_year,
                                "previous_year_net_sales": prev_net_sales
                            })
                    
                    tidy_rows.append(record)
    
    return tidy_rows

def find_relevant_tables(soup, keywords):
    relevant_tables = []
    # Search for all divs and ix:nonnumeric tags that contain a table
    for container in soup.find_all(['div', 'ix:nonnumeric']):
        text = container.get_text(separator=' ', strip=True).lower()
        if any(kw.lower() in text for kw in keywords):
            table = container.find('table')
            if table:
                relevant_tables.append(table)
    return relevant_tables

# --- Main Extraction Logic ---
def extract_10q_summary(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    revenue_tables = find_relevant_tables(soup, ['disaggregated net sales', 'net sales', 'revenue'])
    segment_tables = find_relevant_tables(soup, ['Segment Information and Geographic Data'])
    prod_data = []
    seg_data = []
    if revenue_tables:
        prod_data = tidy_products_services_table(extract_table_data(revenue_tables[0]))
    if segment_tables:
        seg_data = tidy_segment_operating_table(extract_table_data(segment_tables[0]))
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

if __name__ == '__main__':
    main() 