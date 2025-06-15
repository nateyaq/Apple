import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime
import numpy as np
from bs4 import XMLParsedAsHTMLWarning
import warnings
import itertools
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sec_scraper_debug.log')
    ]
)
logger = logging.getLogger(__name__)

CIK = '320193'  # Apple
OUTPUT_JSON = 'apple_sec_sales_data.json'

HEADERS = {'User-Agent': "apple-dashboard@example.com"}

def extract_form_type(text):
    """Extract the form type (10-K or 10-Q) from the filing text."""
    match = re.search(r'Form\s+(10-K|10-Q)', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"

def find_relevant_notes(soup):
    """Find the notes containing revenue and segment information by their content rather than note numbers."""
    revenue_note = None
    segment_note = None
    
    # Look for revenue/product line information
    revenue_patterns = [
        'Net Sales by Product Line',
        'Revenue by Product Line',
        'Net Sales by Product',
        'Revenue by Product',
        'Product Line Information',
        'Product Information',
        'Net Sales by Category',
        'Revenue by Category',
        'Product Category Information'
    ]
    
    # Look for segment/geographic information
    segment_patterns = [
        'Segment Information',
        'Geographic Data',
        'Segment and Geographic Information',
        'Segment and Geographic Data',
        'Segment Reporting',
        'Geographic Information'
    ]
    
    print("[DEBUG] Searching for revenue/product line information...")
    # First try ix:nonnumeric tags
    for pattern in revenue_patterns:
        note_tags = soup.find_all('ix:nonnumeric', attrs={'name': lambda x: x and pattern.lower() in x.lower()})
        if note_tags:
            print(f"[DEBUG] Found revenue note using pattern: {pattern}")
            revenue_note = note_tags
            break
            
    for pattern in segment_patterns:
        note_tags = soup.find_all('ix:nonnumeric', attrs={'name': lambda x: x and pattern.lower() in x.lower()})
        if note_tags:
            print(f"[DEBUG] Found segment note using pattern: {pattern}")
            segment_note = note_tags
            break
    
    # Then try text content
    if not revenue_note:
        print("[DEBUG] No revenue note found in iXBRL tags, trying text content...")
        for pattern in revenue_patterns:
            note_tags = soup.find_all(['p', 'div', 'span', 'b', 'strong'], 
                                    string=lambda x: x and pattern.lower() in x.lower())
            if note_tags:
                print(f"[DEBUG] Found revenue note in text content using pattern: {pattern}")
                revenue_note = note_tags
                break
                
    if not segment_note:
        print("[DEBUG] No segment note found in iXBRL tags, trying text content...")
        for pattern in segment_patterns:
            note_tags = soup.find_all(['p', 'div', 'span', 'b', 'strong'], 
                                    string=lambda x: x and pattern.lower() in x.lower())
            if note_tags:
                print(f"[DEBUG] Found segment note in text content using pattern: {pattern}")
                segment_note = note_tags
                break
    
    if not revenue_note:
        print("[DEBUG] No revenue note found with any pattern")
    if not segment_note:
        print("[DEBUG] No segment note found with any pattern")
    
    return revenue_note, segment_note

def extract_note2_table_text(html):
    soup = BeautifulSoup(html, 'lxml')
    revenue_note, _ = find_relevant_notes(soup)
    if revenue_note:
        tables = extract_tables_after_note(soup, revenue_note[0].get_text(), debug_url=None)
        return tables
    return []

def extract_note10_table_text(html):
    soup = BeautifulSoup(html, 'lxml')
    _, segment_note = find_relevant_notes(soup)
    if segment_note:
        tables = extract_tables_after_note(soup, segment_note[0].get_text(), debug_url=None)
        return tables
    return []

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
    """Extract data from a table, handling both regular HTML tables and iXBRL tables, including nested/merged cells."""
    if not table:
        return None

    # If table contains ix:nonfraction or ix:nonnumeric, treat as iXBRL table
    ix_cells = table.find_all(['ix:nonfraction', 'ix:nonnumeric'])
    if ix_cells:
        print("[DEBUG] Found iXBRL cells")
        # Try to extract rows by traversing <tr> tags
        rows = []
        for tr in table.find_all('tr'):
            row = []
            for td in tr.find_all(['td', 'th'], recursive=False):
                # If the cell contains ix:nonfraction, extract its value
                ix = td.find(['ix:nonfraction', 'ix:nonnumeric'])
                if ix:
                    try:
                        value = float(ix.text.strip().replace(',', ''))
                    except (ValueError, TypeError):
                        value = ix.text.strip()
                    row.append(value)
                else:
                    # Otherwise, use the text content
                    value = td.get_text(separator=' ', strip=True)
                    row.append(value)
            if row:
                rows.append(row)
        
        # If no rows found, try to group by contextRef
        if not rows:
            context_rows = {}
            for cell in ix_cells:
                context_ref = cell.get('contextRef', '')
                if context_ref not in context_rows:
                    context_rows[context_ref] = []
                try:
                    value = float(cell.text.strip().replace(',', ''))
                except (ValueError, TypeError):
                    value = cell.text.strip()
                context_rows[context_ref].append(value)
            rows = list(context_rows.values())
        
        # If still no rows, try to extract data from the cells directly
        if not rows:
            row = []
            for cell in ix_cells:
                try:
                    value = float(cell.text.strip().replace(',', ''))
                except (ValueError, TypeError):
                    value = cell.text.strip()
                row.append(value)
            if row:
                rows.append(row)
        
        return rows

    # For regular HTML tables (non-iXBRL)
    rows = []
    for tr in table.find_all('tr'):
        row = []
        for td in tr.find_all(['td', 'th'], recursive=False):
            # Get text content, handling nested elements
            value = td.get_text(separator=' ', strip=True)
            # Try to convert to float if it looks like a number
            try:
                if re.search(r'[\d,]+', value):
                    value = float(value.replace('$', '').replace(',', '').strip())
            except (ValueError, TypeError):
                pass
            row.append(value)
        if row:
            rows.append(row)
    
    # Clean up the rows
    if rows:
        # Remove empty rows
        rows = [row for row in rows if any(row)]
        # Remove empty columns
        if rows:
            # Find the maximum row length
            max_len = max(len(row) for row in rows)
            # Pad shorter rows with None
            rows = [row + [None] * (max_len - len(row)) for row in rows]
            # Find non-empty columns
            non_empty_cols = [i for i in range(max_len) if any(row[i] for row in rows)]
            # Only keep non-empty columns
            if non_empty_cols:
                rows = [[row[i] for i in non_empty_cols] for row in rows]
    
    return rows

def extract_tables_after_note(soup, note_title, debug_url=None):
    """Extract tables after a specific note title, with special handling for Note 2 and Note 10."""
    tables = []
    
    # Special handling for Note 10 (Segment Information)
    if 'Segment' in note_title:
        # Try iXBRL tags first
        ix_name = 'us-gaap:ScheduleOfSegmentReportingInformationBySegmentTextBlock'
        ix_tables = extract_tables_from_ix_nonnumeric(soup, ix_name)
        for table in ix_tables:
            table_data = extract_table_data(table)
            if table_data:
                tables.append(table_data)
        
        # Try other iXBRL tags that might contain segment data
        ix_names = [
            'us-gaap:SegmentReportingDisclosureTextBlock',
            'us-gaap:SegmentReportingInformationTextBlock',
            'us-gaap:SegmentReportingDisclosureAndOtherInformationTextBlock'
        ]
        for ix_name in ix_names:
            ix_tables = extract_tables_from_ix_nonnumeric(soup, ix_name)
            for table in ix_tables:
                table_data = extract_table_data(table)
                if table_data:
                    tables.append(table_data)
        
        if tables:
            print(f"[DEBUG] Found {len(tables)} Note 10 tables in main doc {debug_url}")
            return tables
    
    # Try more variations for Note 10
    note10_titles = [
        note_title,
        note_title.replace(' – ', '. '),
        note_title.replace(' – ', ' - '),
        note_title.replace(' – ', ': '),
        note_title.replace(' – ', ' '),
        "Note 10 – Segment Information",
        "Note 10. Segment Information",
        "Note 10—Segment Information",
        "Note 10—Segment Information and Geographic Data",
        "Note 10: Segment Information",
        "Note 10: Segment Information and Geographic Data",
        "Segment Information",
        "Geographic Data",
        "Segments",
        "Segment Reporting",
        "Segment and Geographic Information",
        "Segment and Geographic Data"
    ]
    
    # Try to find the note section
    note_section = None
    for try_title in note10_titles:
        note_tags = find_note_section(soup, try_title)
        if note_tags:
            note_section = note_tags
            break
    
    if note_section:
        # Find all tables after the note section
        for tag in note_section:
            current = tag
            while current:
                if current.name == 'table':
                    table_data = extract_table_data(current)
                    if table_data:
                        tables.append(table_data)
                current = current.find_next(['table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if current and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break
    
    # If still not found and this is Note 10, scan all tables for likely headers
    if 'Segment' in note_title or 'Geographic' in note_title or 'segment' in note_title.lower():
        print(f"[DEBUG] Scanning all tables for likely Note 10 headers in {debug_url}")
        for table in soup.find_all('table'):
            table_data = extract_table_data(table)
            if not table_data or len(table_data) < 2:
                continue
            header_row = table_data[0]
            header_text = ' '.join(str(cell).lower() for cell in header_row)
            if any(hint in header_text for hint in ['net sales', 'operating income', 'region', 'geographic', 'americas', 'europe', 'china', 'japan', 'rest of asia']):
                print(f"[DEBUG] Found likely Note 10 table with header: {header_row}")
                tables.append(table_data)
    
    # If still not found, try to find tables with specific patterns
    if not tables:
        for table in soup.find_all('table'):
            table_data = extract_table_data(table)
            if not table_data or len(table_data) < 2:
                continue
            # Check if table has any of the expected headers
            headers = [str(cell).lower() for cell in table_data[0]]
            if any(hint in ' '.join(headers) for hint in ['net sales', 'operating income', 'region', 'geographic', 'americas', 'europe', 'china', 'japan', 'rest of asia']):
                tables.append(table_data)
    
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
def parse_note2_periods(rows):
    """Parse period labels and product values from Note 2 table."""
    # Find the header row with period types and dates
    period_labels = []
    date_pattern = r'([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    header_row_idx = None
    for i, row in enumerate(rows):
        if any(isinstance(cell, str) and ("Three Months Ended" in cell or "Nine Months Ended" in cell or "Six Months Ended" in cell or "Year Ended" in cell) for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None or header_row_idx + 2 >= len(rows):
        return []
    # The next two rows are usually the date row and the $ row
    period_type_row = rows[header_row_idx]
    date_row = rows[header_row_idx + 1]
    # Build period labels
    for i, cell in enumerate(period_type_row):
        if isinstance(cell, str):
            match = re.search(date_pattern, str(date_row[i])) if i < len(date_row) and isinstance(date_row[i], str) else None
            if "Three Months Ended" in cell:
                if match:
                    period_labels.append(f"Three Months Ended {match.group(1)}")
                else:
                    period_labels.append("Three Months Ended")
            elif "Six Months Ended" in cell:
                if match:
                    period_labels.append(f"Six Months Ended {match.group(1)}")
                else:
                    period_labels.append("Six Months Ended")
            elif "Nine Months Ended" in cell:
                if match:
                    period_labels.append(f"Nine Months Ended {match.group(1)}")
                else:
                    period_labels.append("Nine Months Ended")
            elif "Year Ended" in cell:
                if match:
                    period_labels.append(f"Year Ended {match.group(1)}")
                else:
                    period_labels.append("Year Ended")
    # Now parse each product row
    products = []
    for row in rows[header_row_idx + 3:]:
        if not row or not isinstance(row[0], str):
            continue
        product = row[0].strip()
        if not product or product.lower().startswith('total'):
            continue
        values = {}
        for i, label in enumerate(period_labels):
            if i + 1 < len(row):
                try:
                    val = row[i + 1]
                    if isinstance(val, (int, float)):
                        values[label] = val
                    elif isinstance(val, str):
                        val_clean = val.replace('$', '').replace(',', '').strip()
                        if val_clean:
                            values[label] = float(val_clean)
                except Exception:
                    continue
        if values:
            products.append({"product": product, "values": values})
    return products

def parse_note10_periods(rows):
    """Parse period labels and region/metric values from Note 10/11 table."""
    # Find the header row with period types and dates
    period_labels = []
    date_pattern = r'([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    header_row_idx = None
    for i, row in enumerate(rows):
        if any(isinstance(cell, str) and ("Three Months Ended" in cell or "Nine Months Ended" in cell or "Six Months Ended" in cell or "Year Ended" in cell) for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None or header_row_idx + 2 >= len(rows):
        return []
    period_type_row = rows[header_row_idx]
    date_row = rows[header_row_idx + 1]
    # Build period labels
    for i, cell in enumerate(period_type_row):
        if isinstance(cell, str):
            match = re.search(date_pattern, str(date_row[i])) if i < len(date_row) and isinstance(date_row[i], str) else None
            if "Three Months Ended" in cell:
                if match:
                    period_labels.append(f"Three Months Ended {match.group(1)}")
                else:
                    period_labels.append("Three Months Ended")
            elif "Six Months Ended" in cell:
                if match:
                    period_labels.append(f"Six Months Ended {match.group(1)}")
                else:
                    period_labels.append("Six Months Ended")
            elif "Nine Months Ended" in cell:
                if match:
                    period_labels.append(f"Nine Months Ended {match.group(1)}")
                else:
                    period_labels.append("Nine Months Ended")
            elif "Year Ended" in cell:
                if match:
                    period_labels.append(f"Year Ended {match.group(1)}")
                else:
                    period_labels.append("Year Ended")
    # Now parse each region/metric row
    regions = []
    current_region = None
    for row in rows[header_row_idx + 3:]:
        if not row or not isinstance(row[0], str):
            continue
        cell = row[0].strip()
        if not cell:
            continue
        # Region header
        if cell.endswith(":"):
            current_region = cell[:-1]
            continue
        # Metric row (Net sales, Operating income, etc.)
        if current_region and ("Net sales" in cell or "Operating income" in cell):
            metric = cell
            values = {}
            for i, label in enumerate(period_labels):
                if i + 1 < len(row):
                    try:
                        val = row[i + 1]
                        if isinstance(val, (int, float)):
                            values[label] = val
                        elif isinstance(val, str):
                            val_clean = val.replace('$', '').replace(',', '').strip()
                            if val_clean:
                                values[label] = float(val_clean)
                    except Exception:
                        continue
            if values:
                regions.append({"region": current_region, "metric": metric, "values": values})
    return regions

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

def extract_segment_data(note10_text):
    """Extract segment data from Note 10 text."""
    data = {
        'periods': [],
        'metrics': {
            'Net sales': {},
            'Operating income': {}
        }
    }
    
    # Extract periods using regex
    period_pattern = r'(?:Three|Six) Months Ended\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    periods = re.findall(period_pattern, note10_text)
    data['periods'] = periods
    
    # Process each line to extract segment data
    lines = note10_text.split('\n')
    current_segment = None
    current_metric = None
    
    for line in lines:
        # Check for segment headers
        if any(segment in line for segment in ['Americas:', 'Europe:', 'Greater China:', 'Japan:', 'Rest of Asia Pacific:']):
            current_segment = line.split(':')[0].strip()
            continue
            
        # Check for metrics
        if 'Net sales' in line:
            current_metric = 'Net sales'
            continue
        elif 'Operating income' in line:
            current_metric = 'Operating income'
            continue
            
        # Extract values if we have a current segment and metric
        if current_segment and current_metric:
            # Extract values using regex
            value_pattern = r'\$([\d,]+)'
            values = re.findall(value_pattern, line)
            
            if values:
                # Convert string values to float and store in data structure
                for i, value in enumerate(values):
                    if i < len(periods):
                        period = periods[i]
                        if current_segment not in data['metrics'][current_metric]:
                            data['metrics'][current_metric][current_segment] = {}
                        data['metrics'][current_metric][current_segment][period] = float(value.replace(',', ''))
    
    return data

def extract_notes_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    notes = {}
    
    # Find Revenue data
    revenue_tables = extract_tables_after_note(soup, "Revenue")
    if revenue_tables:
        notes["Revenue"] = revenue_tables
    
    # Find Segment Information and Geographic Data
    segment_tables = extract_tables_after_note(soup, "Segment Information and Geographic Data")
    if segment_tables:
        notes["Segment Information and Geographic Data"] = segment_tables
    
    return notes

def aggregate_note2_periods(note2_tables):
    if not note2_tables:
        return []
    aggregated_data = []
    for table in note2_tables:
        periods = parse_note2_periods(table)
        for entry in periods:
            # Wrap each value in a dict with 'value' key
            values = {k: {"value": v} for k, v in entry["values"].items()}
            aggregated_data.append({"product": entry["product"], "values": values})
    return aggregated_data

def aggregate_note10_periods(note10_tables):
    if not note10_tables:
        return []
    aggregated_data = []
    for table in note10_tables:
        periods = parse_note10_periods(table)
        for entry in periods:
            # Wrap each value in a dict with 'value' key
            values = {k: {"value": v} for k, v in entry["values"].items()}
            aggregated_data.append({"region": entry["region"], "metric": entry["metric"], "values": values})
    return aggregated_data

def scrape_sales_data():
    filings = []
    # Get latest 10-K and 10-Q filings
    annual_urls = get_latest_filing_urls(form_type='10-K', count=5)
    quarterly_urls = get_latest_filing_urls(form_type='10-Q', count=5)
    for url in annual_urls + quarterly_urls:
        try:
            html_content = get_sec_html(url['url'])
            if not html_content:
                continue
            # Extract notes
            notes = extract_notes_from_html(html_content)
            # Process Revenue data
            note2_data = []
            if "Revenue" in notes:
                note2_data = aggregate_note2_periods(notes["Revenue"])
            # Process Segment Information and Geographic Data
            note10_data = []
            if "Segment Information and Geographic Data" in notes:
                note10_data = aggregate_note10_periods(notes["Segment Information and Geographic Data"])
            # Create filing entry
            filing = {
                "date": url['date'],
                "accession": url['accession'],
                "form_type": extract_form_type(html_content),
                "note2": note2_data,
                "note10": note10_data,
                "url": url['url']
            }
            filings.append(filing)
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            continue
    # Sort filings by date
    filings.sort(key=lambda x: x["date"], reverse=True)
    # Save to JSON
    with open('apple_sec_sales_data.json', 'w') as f:
        json.dump({"filings": filings}, f, indent=2)
    return filings

def main():
    scrape_sales_data()

if __name__ == '__main__':
    main() 