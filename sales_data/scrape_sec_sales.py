import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime
import numpy as np
from bs4 import XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

CIK = '320193'  # Apple
OUTPUT_JSON = "sales_data/apple_sec_sales_data.json"

HEADERS = {'User-Agent': "apple-dashboard@example.com"}

# Get the latest N filings of a given type (10-K or 10-Q)
def get_latest_filing_urls(cik=CIK, form_type='10-Q', count=5):
    url = f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json'
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    filings = data['filings']['recent']
    urls = []
    for i, form in enumerate(filings['form']):
        if form == form_type:
            accession = filings['accessionNumber'][i].replace('-', '')
            primary_doc = filings['primaryDocument'][i]
            filing_date = filings['filingDate'][i]
            doc_url = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}'
            urls.append({'url': doc_url, 'date': filing_date, 'accession': filings['accessionNumber'][i]})
            if len(urls) >= count:
                break
    return urls

def get_sec_html(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.text

def find_note_section(soup, note_title):
    """Find the section containing the note title"""
    # Try different patterns for note titles
    patterns = [
        note_title,
        note_title.replace(' – ', '. '),
        note_title.replace(' – ', ' - '),
        note_title.replace(' – ', ': '),
        note_title.replace(' – ', ' ')
    ]
    
    # First try ix:nonnumeric tags
    for pattern in patterns:
        note_tags = soup.find_all('ix:nonnumeric', attrs={'name': lambda x: x and pattern.lower() in x.lower()})
        if note_tags:
            return note_tags
    
    # Then try text content
    for pattern in patterns:
        note_tags = soup.find_all(['p', 'div', 'span', 'b', 'strong'], 
                                string=lambda x: x and pattern.lower() in x.lower())
        if note_tags:
            return note_tags
    
    return []

def extract_tables_from_ix_nonnumeric(soup, ix_name):
    """Extract tables from iXBRL nonnumeric tags."""
    tables = []
    for tag in soup.find_all('ix:nonnumeric', attrs={'name': ix_name}):
        # Find the parent table or create a new one
        table = tag.find_parent('table')
        if not table:
            # Create a new table structure
            table = soup.new_tag('table')
            # Add the content as a row
            tr = soup.new_tag('tr')
            td = soup.new_tag('td')
            td.append(tag)
            tr.append(td)
            table.append(tr)
        tables.append(table)
    return tables

def extract_table_data(table):
    """Extract data from a table, handling both regular HTML tables and iXBRL tables."""
    if not table:
        return None

    # For iXBRL tables, look for ix:nonfraction tags
    ix_cells = table.find_all(['ix:nonfraction', 'ix:nonnumeric'])
    if ix_cells:
        print("[DEBUG] Found iXBRL cells")
        # Group cells by row using contextRef
        rows = {}
        for cell in ix_cells:
            context_ref = cell.get('contextRef', '')
            if context_ref not in rows:
                rows[context_ref] = []
            # Try to convert to float if possible
            try:
                value = float(cell.text.strip().replace(',', ''))
            except (ValueError, TypeError):
                value = cell.text.strip()
            rows[context_ref].append(value)
        return list(rows.values())

    # For regular HTML tables
    rows = []
    for tr in table.find_all('tr'):
        row = []
        for td in tr.find_all(['td', 'th']):
            # Try to convert to float if possible
            try:
                value = float(td.text.strip().replace(',', ''))
            except (ValueError, TypeError):
                value = td.text.strip()
            row.append(value)
        if row:  # Only add non-empty rows
            rows.append(row)
    return rows

def extract_tables_after_note(soup, note_title, debug_url=None):
    """Extract tables after a specific note title, with special handling for Note 2 and Note 10."""
    tables = []
    # Special handling for Note 10 (Segment Information)
    if 'Segment' in note_title:
        ix_name = 'us-gaap:ScheduleOfSegmentReportingInformationBySegmentTextBlock'
        ix_tables = extract_tables_from_ix_nonnumeric(soup, ix_name)
        for idx, table in enumerate(ix_tables):
            first_tr = table.find('tr')
            if first_tr:
                print(f"[DEBUG] Note 10: Full HTML of first <tr> in table {idx}:\n{str(first_tr)}\n---")
            table_data = extract_table_data(table)
            print(f"[DEBUG] Note 10: First 2 rows of extracted table: {table_data[:2]}")
            if table_data:
                tables.append(table_data)
        if tables:
            print(f"[DEBUG] Found {len(tables)} Note 10 tables in main doc {debug_url}")
            return tables

    # Find the note title
    note_header = None
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div']):
        if note_title.lower() in tag.text.lower():
            note_header = tag
            break

    if not note_header:
        print(f"[DEBUG] Could not find note header: {note_title} in {debug_url}")
        return []

    # Find all tables after the note header
    current = note_header
    while current:
        if current.name == 'table':
            table_data = extract_table_data(current)
            print(f"[DEBUG] Table after note header: First 2 rows: {table_data[:2] if table_data else 'None'}")
            if table_data:
                tables.append(table_data)
        current = current.find_next(['table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if current and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            break

    print(f"[DEBUG] Found {len(tables)} tables after note header in {debug_url}")
    return tables

def table_to_df(table_data):
    """Convert table data to pandas DataFrame"""
    if not table_data:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(table_data)
    
    # Clean up column names
    if df.shape[0] > 0:
        # Get the first row that contains any non-empty values
        first_valid_row = None
        for i, row in df.iterrows():
            if any(pd.notna(x) for x in row):
                first_valid_row = i
                break
        
        if first_valid_row is not None:
            # Use this row as header
            df.columns = [str(x).strip() if pd.notna(x) else f'col_{i}' for i, x in enumerate(df.iloc[first_valid_row])]
            df = df.iloc[first_valid_row + 1:]
        else:
            # If no valid row found, use default column names
            df.columns = [f'col_{i}' for i in range(len(df.columns))]
    
    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]
    
    # Remove rows where all values are None/NaN
    df = df.dropna(how='all')
    
    # Remove columns where all values are None/NaN
    df = df.dropna(axis=1, how='all')
    
    return df

def df_to_json(df):
    """Convert DataFrame to JSON-serializable format, converting 4-digit float years to int."""
    if df.empty:
        return []
    
    # Convert DataFrame to records, handling duplicate columns
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            value = row[col]
            # If value is a Series (can happen with duplicate columns), take the first value or convert to string
            if isinstance(value, pd.Series):
                if not value.empty:
                    value = value.iloc[0]
                else:
                    value = None
            # Convert numpy/pandas types to Python native types
            if pd.isna(value):
                record[col] = None
            elif isinstance(value, (np.int64, int)):
                record[col] = int(value)
            elif isinstance(value, float):
                # If value is a 4-digit float (e.g., 2024.0), convert to int
                if value.is_integer() and 1000 <= int(value) <= 2999:
                    record[col] = int(value)
                else:
                    record[col] = value
            else:
                record[col] = value
        records.append(record)
    
    return records

# --- New helper functions for structured extraction ---
def parse_note2_periods(table_data):
    if not table_data or len(table_data) < 2:
        print("Note 2: Empty or too short table_data")
        return []
    print(f"[DEBUG] Note 2: First 2 rows of extracted table: {table_data[:2]}")
    # Find header row: look for any row with a year or 'ended' in it
    header_row_idx = None
    for i, row in enumerate(table_data):
        if any(re.search(r"(\d{4}|ended)", str(cell), re.I) for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        print("[DEBUG] Note 2: No header row found")
        return []
    header_row = table_data[header_row_idx]
    print(f"[DEBUG] Note 2: Column labels: {header_row}")
    # Find date columns: any cell with a year
    date_cols = [i for i, cell in enumerate(header_row) if re.search(r"20\d{2}", str(cell))]
    if not date_cols:
        print("[DEBUG] Note 2: No date columns found")
        return []
    print(f"[DEBUG] Note 2: Found date columns: {date_cols}")
    periods = []
    for row in table_data[header_row_idx+1:]:
        if not row or not any(cell for cell in row):
            continue
        first_cell = str(row[0]).strip()
        # Loosen: skip only if cell is empty or looks like a subtotal/total
        if not first_cell or re.search(r"total|margin|tax|expenses?|development|income", first_cell, re.I):
            continue
        values = {}
        for col in date_cols:
            if col < len(row) and row[col] is not None:
                try:
                    value = float(str(row[col]).replace(',', ''))
                    date_str = header_row[col]
                    values[date_str] = {'value': value}
                except (ValueError, TypeError):
                    continue
        if values:
            period = {'product': first_cell, 'values': values}
            periods.append(period)
    print(f"[DEBUG] Note 2: Found {len(periods)} periods with data")
    return periods

def parse_note10_periods(table_data):
    if not table_data or len(table_data) < 2:
        print("Note 10: Empty or too short table_data")
        return []
    print(f"[DEBUG] Note 10: First 2 rows of extracted table: {table_data[:2]}")
    header_row_idx = None
    for i, row in enumerate(table_data):
        if any(re.search(r"(\d{4}|ended)", str(cell), re.I) for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        print("[DEBUG] Note 10: No header row found")
        return []
    header_row = table_data[header_row_idx]
    print(f"[DEBUG] Note 10: Column labels: {header_row}")
    date_cols = [i for i, cell in enumerate(header_row) if re.search(r"20\d{2}", str(cell))]
    if not date_cols:
        print("[DEBUG] Note 10: No date columns found")
        return []
    print(f"[DEBUG] Note 10: Found date columns: {date_cols}")
    periods = []
    current_region = None
    for row in table_data[header_row_idx+1:]:
        if not row or not any(cell for cell in row):
            continue
        first_cell = str(row[0]).strip()
        # Loosen: treat any cell ending with ':' as a region, otherwise look for metrics
        if first_cell.endswith(':'):
            current_region = first_cell[:-1]
            continue
        if current_region and re.search(r"net sales|operating income", first_cell, re.I):
            values = {}
            for col in date_cols:
                if col < len(row) and row[col] is not None:
                    try:
                        value = float(str(row[col]).replace(',', ''))
                        date_str = header_row[col]
                        values[date_str] = {'value': value}
                    except (ValueError, TypeError):
                        continue
            if values:
                period = {'region': current_region, 'metric': first_cell, 'values': values}
                periods.append(period)
    print(f"[DEBUG] Note 10: Found {len(periods)} periods with data")
    return periods

# --- Helper to fetch and parse exhibits if main doc is empty ---
def fetch_and_parse_exhibits(main_html, base_url, note_title):
    soup = BeautifulSoup(main_html, 'lxml')
    # Look for exhibit links (EX-101, Inline XBRL, etc.)
    exhibit_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text().lower()
        if 'ex-101' in text or 'inline xbrl' in text or 'ex-101' in href or 'xbrl' in href:
            if not href.startswith('http'):
                # Make absolute
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
            exhibit_links.append(href)
    print(f"[DEBUG] Found {len(exhibit_links)} exhibit links for {note_title}")
    for ex_url in exhibit_links:
        try:
            print(f"[DEBUG] Fetching exhibit: {ex_url}")
            ex_html = get_sec_html(ex_url)
            ex_soup = BeautifulSoup(ex_html, 'lxml')
            tables = extract_tables_after_note(ex_soup, note_title, debug_url=ex_url)
            if tables:
                print(f"[DEBUG] Found {len(tables)} tables in exhibit {ex_url}")
                return tables
        except Exception as e:
            print(f"[DEBUG] Error fetching/parsing exhibit {ex_url}: {e}")
    return []

def scrape_sales_data():
    output = {'annual': [], 'quarterly': []}

    # Annual (10-K)
    for filing in get_latest_filing_urls(CIK, '10-K', 5):
        print(f"\nProcessing annual filing: {filing['date']}")
        html = get_sec_html(filing['url'])
        soup = BeautifulSoup(html, 'lxml')
        # Extract Note 2 (Revenue) tables
        note2_tables = extract_tables_after_note(soup, "Note 2 – Revenue", debug_url=filing['url'])
        if not note2_tables:
            note2_tables = extract_tables_after_note(soup, "Note 2. Revenue", debug_url=filing['url'])
            if not note2_tables:
                note2_tables = extract_tables_after_note(soup, "Note 2—Revenue", debug_url=filing['url'])
                if not note2_tables:
                    note2_tables = extract_tables_after_note(soup, "Note 2—Revenue Recognition", debug_url=filing['url'])
        # If still empty, try exhibits
        if not note2_tables:
            note2_tables = fetch_and_parse_exhibits(html, filing['url'], "Note 2")
        # Extract Note 10 (Segment Information) tables
        note10_tables = extract_tables_after_note(soup, "Note 10 – Segment Information and Geographic Data", debug_url=filing['url'])
        if not note10_tables:
            note10_tables = extract_tables_after_note(soup, "Note 10. Segment Information", debug_url=filing['url'])
            if not note10_tables:
                note10_tables = extract_tables_after_note(soup, "Note 10—Segment Information", debug_url=filing['url'])
                if not note10_tables:
                    note10_tables = extract_tables_after_note(soup, "Note 10—Segment Information and Geographic Data", debug_url=filing['url'])
        if not note10_tables:
            note10_tables = fetch_and_parse_exhibits(html, filing['url'], "Note 10")
        print(f"[DEBUG] Found {len(note2_tables)} Note 2 tables and {len(note10_tables)} Note 10 tables")
        note2_periods = []
        for t in note2_tables:
            periods = parse_note2_periods(t)
            if periods:
                note2_periods.extend(periods)
                print(f"[DEBUG] Added {len(periods)} periods from Note 2 table")
        note10_periods = []
        for t in note10_tables:
            periods = parse_note10_periods(t)
            if periods:
                note10_periods.extend(periods)
                print(f"[DEBUG] Added {len(periods)} periods from Note 10 table")
        output['annual'].append({
            'date': filing['date'],
            'accession': filing['accession'],
            'note2_periods': note2_periods,
            'note10_periods': note10_periods,
            'url': filing['url']
        })
    # Quarterly (10-Q)
    for filing in get_latest_filing_urls(CIK, '10-Q', 5):
        print(f"\nProcessing quarterly filing: {filing['date']}")
        html = get_sec_html(filing['url'])
        soup = BeautifulSoup(html, 'lxml')
        note2_tables = extract_tables_after_note(soup, "Note 2 – Revenue", debug_url=filing['url'])
        if not note2_tables:
            note2_tables = extract_tables_after_note(soup, "Note 2. Revenue", debug_url=filing['url'])
            if not note2_tables:
                note2_tables = extract_tables_after_note(soup, "Note 2—Revenue", debug_url=filing['url'])
                if not note2_tables:
                    note2_tables = extract_tables_after_note(soup, "Note 2—Revenue Recognition", debug_url=filing['url'])
        if not note2_tables:
            note2_tables = fetch_and_parse_exhibits(html, filing['url'], "Note 2")
        note10_tables = extract_tables_after_note(soup, "Note 10 – Segment Information and Geographic Data", debug_url=filing['url'])
        if not note10_tables:
            note10_tables = extract_tables_after_note(soup, "Note 10. Segment Information", debug_url=filing['url'])
            if not note10_tables:
                note10_tables = extract_tables_after_note(soup, "Note 10—Segment Information", debug_url=filing['url'])
                if not note10_tables:
                    note10_tables = extract_tables_after_note(soup, "Note 10—Segment Information and Geographic Data", debug_url=filing['url'])
        if not note10_tables:
            note10_tables = fetch_and_parse_exhibits(html, filing['url'], "Note 10")
        print(f"[DEBUG] Found {len(note2_tables)} Note 2 tables and {len(note10_tables)} Note 10 tables")
        note2_periods = []
        for t in note2_tables:
            periods = parse_note2_periods(t)
            if periods:
                note2_periods.extend(periods)
                print(f"[DEBUG] Added {len(periods)} periods from Note 2 table")
        note10_periods = []
        for t in note10_tables:
            periods = parse_note10_periods(t)
            if periods:
                note10_periods.extend(periods)
                print(f"[DEBUG] Added {len(periods)} periods from Note 10 table")
        output['quarterly'].append({
            'date': filing['date'],
            'accession': filing['accession'],
            'note2_periods': note2_periods,
            'note10_periods': note10_periods,
            'url': filing['url']
        })
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nExtracted sales data for last 5 years (annual) and last 5 quarters (quarterly) saved to {OUTPUT_JSON}")

def main():
    scrape_sales_data()

if __name__ == '__main__':
    main() 