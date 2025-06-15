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
import argparse
import time

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Set paths for output files in the sales_data directory
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / 'sec_scraper_debug.log'
OUTPUT_JSON = SCRIPT_DIR / 'apple_sec_sales_data.json'

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

logger.debug('--- Script started: Logging is working ---')

CIK = '320193'  # Apple

HEADERS = {'User-Agent': "apple-dashboard@example.com"}

def get_arg_parser():
    parser = argparse.ArgumentParser(description="Apple SEC Sales Data Scraper")
    parser.add_argument('--mode', choices=['robust', 'fast'], default='robust', help='Search mode: robust (all possible note titles) or fast (most likely only)')
    parser.add_argument('--include-extra', action='store_true', help='Include extra data points (e.g., gross margin, total net sales, etc.) in output')
    parser.add_argument('--url', type=str, default=None, help='Specific SEC filing URL to process')
    return parser

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
        'Product Category Information',
        'Note 2',
        'Note 2—',
        'Note 2 -',
        'Note 2.',
        'Note 2:',
        'Note 2 Revenue',
        'Note 2—Revenue',
        'Note 2 - Revenue',
        'Note 2. Revenue',
        'Note 2: Revenue',
        'Segment Operating Performance',
        'Products and Services Performance'
    ]
    
    # Look for segment/geographic information
    segment_patterns = [
        'Segment Information',
        'Geographic Data',
        'Segment and Geographic Information',
        'Segment and Geographic Data',
        'Segment Reporting',
        'Geographic Information',
        'Note 10',
        'Note 10—',
        'Note 10 -',
        'Note 10.',
        'Note 10:',
        'Note 10 Segment',
        'Note 10—Segment',
        'Note 10 - Segment',
        'Note 10. Segment',
        'Note 10: Segment',
        'Segment Operating Performance',
        'Products and Services Performance'
    ]
    
    logger.debug("[DEBUG] Searching for revenue/product line information...")
    # First try ix:nonnumeric tags
    for pattern in revenue_patterns:
        note_tags = soup.find_all('ix:nonnumeric', attrs={'name': lambda x: x and pattern.lower() in x.lower()})
        if note_tags:
            logger.debug(f"[DEBUG] Found revenue note using pattern: {pattern}")
            revenue_note = note_tags
            break
            
    for pattern in segment_patterns:
        note_tags = soup.find_all('ix:nonnumeric', attrs={'name': lambda x: x and pattern.lower() in x.lower()})
        if note_tags:
            logger.debug(f"[DEBUG] Found segment note using pattern: {pattern}")
            segment_note = note_tags
            break
    
    # Then try text content
    if not revenue_note:
        logger.debug("[DEBUG] No revenue note found in iXBRL tags, trying text content...")
        for pattern in revenue_patterns:
            note_tags = soup.find_all(['p', 'div', 'span', 'b', 'strong', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'], 
                                    string=lambda x: x and pattern.lower() in x.lower())
            if note_tags:
                logger.debug(f"[DEBUG] Found revenue note in text content using pattern: {pattern}")
                logger.debug(f"[DEBUG] Found text: {note_tags[0].get_text()}")
                revenue_note = note_tags
                break
                
    if not segment_note:
        logger.debug("[DEBUG] No segment note found in iXBRL tags, trying text content...")
        for pattern in segment_patterns:
            note_tags = soup.find_all(['p', 'div', 'span', 'b', 'strong', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'], 
                                    string=lambda x: x and pattern.lower() in x.lower())
            if note_tags:
                logger.debug(f"[DEBUG] Found segment note in text content using pattern: {pattern}")
                logger.debug(f"[DEBUG] Found text: {note_tags[0].get_text()}")
                segment_note = note_tags
                break
    
    if not revenue_note:
        logger.debug("[DEBUG] No revenue note found with any pattern")
    if not segment_note:
        logger.debug("[DEBUG] No segment note found with any pattern")
    
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
    logger.debug(f"[HTTP] Fetching URL: {url}")
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

def clean_numeric_value(value):
    """Clean and convert a value to numeric if possible."""
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return None
        
    # Remove currency symbols, parentheses, and other non-numeric characters
    value = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
    value = value.replace('%', '').strip()
    
    # Handle special cases
    if value.lower() in ['n/a', 'na', '-', '--', '']:
        return None
        
    try:
        return float(value)
    except (ValueError, TypeError):
        return value.strip()

def extract_table_data(table):
    """Extract data from a table, handling both regular HTML tables and iXBRL tables, including nested/merged cells."""
    if not table:
        return None

    # If table contains ix:nonfraction or ix:nonnumeric, treat as iXBRL table
    ix_cells = table.find_all(['ix:nonfraction', 'ix:nonnumeric'])
    if ix_cells:
        # Try to extract rows by traversing <tr> tags
        rows = []
        for tr in table.find_all('tr'):
            row = []
            for td in tr.find_all(['td', 'th'], recursive=False):
                # Handle rowspan and colspan
                rowspan = int(td.get('rowspan', 1))
                colspan = int(td.get('colspan', 1))
                
                # If the cell contains ix:nonfraction, extract its value
                ix = td.find(['ix:nonfraction', 'ix:nonnumeric'])
                if ix:
                    value = clean_numeric_value(ix.text.strip())
                    # Add the value for each colspan
                    for _ in range(colspan):
                        row.append(value)
                else:
                    # Otherwise, use the text content
                    value = td.get_text(separator=' ', strip=True)
                    # Try to convert to numeric if it looks like a number
                    value = clean_numeric_value(value)
                    # Add the value for each colspan
                    for _ in range(colspan):
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
                value = clean_numeric_value(cell.text.strip())
                context_rows[context_ref].append(value)
            rows = list(context_rows.values())
        
        # If still no rows, try to extract data from the cells directly
        if not rows:
            row = []
            for cell in ix_cells:
                value = clean_numeric_value(cell.text.strip())
                row.append(value)
            if row:
                rows.append(row)
        
        return rows

    # For regular HTML tables (non-iXBRL)
    rows = []
    for tr in table.find_all('tr'):
        row = []
        for td in tr.find_all(['td', 'th'], recursive=False):
            # Handle rowspan and colspan
            rowspan = int(td.get('rowspan', 1))
            colspan = int(td.get('colspan', 1))
            
            # Get text content, handling nested elements
            value = td.get_text(separator=' ', strip=True)
            # Clean and convert to numeric if possible
            value = clean_numeric_value(value)
            # Add the value for each colspan
            for _ in range(colspan):
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

def normalize_header(text):
    if not text:
        return ''
    return text.lower().replace('–', '-').replace('—', '-').replace(':', '').replace('.', '').replace('  ', ' ').strip()

def extract_tables_after_note(soup, note_title, debug_url=None):
    start_time = time.time()
    tables = []
    seen_tables = set()  # Track already-seen tables by id

    def log_and_append(table_data, section_label, method):
        table_id = id(table_data)
        if table_id in seen_tables:
            return
        seen_tables.add(table_id)
        header = table_data[0] if len(table_data) > 0 else None
        first_row = table_data[1] if len(table_data) > 1 else None
        logger.debug(f"[TABLE][{section_label}][{method}] Appending table id={table_id}. Header: {header}, First row: {first_row}")
        tables.append(table_data)

    # Step 1: Prioritized search for common note/section headers
    prioritized_titles = []
    if 'Segment' in note_title or 'Geographic' in note_title or 'segment' in note_title.lower():
        prioritized_titles = [normalize_header(t) for t in [
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
            "Segment and Geographic Data",
            "Segment Operating Performance",
            "Products and Services Performance"
        ]]
    elif 'Revenue' in note_title or 'Product' in note_title or 'note 2' in note_title.lower():
        prioritized_titles = [normalize_header(t) for t in [
            "Note 2 – Revenue",
            "Note 2. Revenue",
            "Note 2—Revenue",
            "Note 2: Revenue",
            "Revenue by Product Line",
            "Net Sales by Product Line",
            "Revenue by Product",
            "Net Sales by Product",
            "Product Line Information",
            "Product Information",
            "Net Sales by Category",
            "Revenue by Category",
            "Product Category Information",
            "Segment Operating Performance",
            "Products and Services Performance"
        ]]
    # Always include the original note_title as first try
    if normalize_header(note_title) not in prioritized_titles:
        prioritized_titles = [normalize_header(note_title)] + prioritized_titles

    found_by_priority = False
    for try_title in prioritized_titles:
        note_tags = find_note_section(soup, try_title)
        if note_tags:
            # Find all tables after the note section
            for tag in note_tags:
                current = tag
                while current:
                    if current.name == 'table':
                        table_data = extract_table_data(current)
                        if table_data:
                            log_and_append(table_data, note_title, 'priority-header')
                            found_by_priority = True
                    current = current.find_next(['table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if current and current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        break
            if tables:
                logger.debug(f"[DEBUG] Found {len(tables)} tables after prioritized note header in {debug_url}")
                logger.debug(f"[TIMER] extract_tables_after_note for '{note_title}' took {time.time() - start_time:.2f}s")
                return tables
    # Step 2: Fallback - scan all tables for likely headers
    logger.debug(f"[DEBUG] No tables found by priority headers, scanning all tables for likely headers in {debug_url}")
    for table in soup.find_all('table'):
        table_data = extract_table_data(table)
        if not table_data or len(table_data) < 2:
            continue
        header_row = table_data[0]
        header_text = normalize_header(' '.join(str(cell) for cell in header_row))
        if any(hint in header_text for hint in ['net sales', 'operating income', 'region', 'geographic', 'americas', 'europe', 'china', 'japan', 'rest of asia', 'product', 'revenue']):
            log_and_append(table_data, note_title, 'fallback-header')
    logger.debug(f"[DEBUG] Found {len(tables)} tables after fallback header scan in {debug_url}")
    logger.debug(f"[TIMER] extract_tables_after_note for '{note_title}' took {time.time() - start_time:.2f}s")
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
# Add a helper to get all prioritized section headers for revenue and segment
REVENUE_SECTION_HEADERS = [
    "Note 2", "Note 2 – Revenue", "Note 2. Revenue", "Note 2—Revenue", "Note 2: Revenue",
    "Revenue by Product Line", "Net Sales by Product Line", "Revenue by Product", "Net Sales by Product",
    "Product Line Information", "Product Information", "Net Sales by Category", "Revenue by Category",
    "Product Category Information", "Products and Services Performance"
]
SEGMENT_SECTION_HEADERS = [
    "Note 10", "Note 10 – Segment Information", "Note 10. Segment Information", "Note 10—Segment Information",
    "Note 10—Segment Information and Geographic Data", "Note 10: Segment Information",
    "Note 10: Segment Information and Geographic Data",
    "Note 11", "Note 11 – Segment Information", "Note 11. Segment Information", "Note 11—Segment Information",
    "Note 11—Segment Information and Geographic Data", "Note 11: Segment Information", "Note 11: Segment Information and Geographic Data",
    "Segment Information", "Geographic Data",
    "Segments", "Segment Reporting", "Segment and Geographic Information", "Segment and Geographic Data",
    "Segment Operating Performance", "Products and Services Performance"
]

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
    logger.debug(f"[DEBUG] Found {len(exhibit_links)} exhibit links for {note_title}")
    for ex_url in exhibit_links:
        try:
            logger.debug(f"[DEBUG] Fetching exhibit: {ex_url}")
            ex_html = get_sec_html(ex_url)
            ex_soup = BeautifulSoup(ex_html, 'lxml')
            tables = extract_tables_after_note(ex_soup, note_title, debug_url=ex_url)
            if tables:
                logger.debug(f"[DEBUG] Found {len(tables)} tables in exhibit {ex_url}")
                return tables
        except Exception as e:
            logger.debug(f"[DEBUG] Error fetching/parsing exhibit {ex_url}: {e}")
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

def find_summary_table_by_header(soup, keywords, region_labels, product_labels):
    """Find a summary table by checking if its header or first row contains any of the given keywords or labels."""
    for table in soup.find_all('table'):
        table_data = extract_table_data(table)
        if not table_data or len(table_data) < 2:
            continue
        header_row = table_data[0]
        first_row = table_data[1]
        header_text = ' '.join(str(cell).lower() for cell in header_row)
        first_row_text = ' '.join(str(cell).lower() for cell in first_row)
        if any(keyword.lower() in header_text or keyword.lower() in first_row_text for keyword in keywords) or \
           any(label.lower() in header_text or label.lower() in first_row_text for label in region_labels) or \
           any(label.lower() in header_text or label.lower() in first_row_text for label in product_labels):
            return table_data
    return None

def validate_table_structure(table_data):
    """Validate the structure of a table to ensure it contains valid data."""
    if not table_data or len(table_data) < 2:
        return False
        
    # Check header row
    header_row = table_data[0]
    if not any(header_row):
        return False
        
    # Check for numeric data in subsequent rows
    has_numeric_data = False
    for row in table_data[1:]:
        if not row:
            continue
        # Check if row contains any numeric values
        if any(isinstance(cell, (int, float)) for cell in row):
            has_numeric_data = True
            break
            
    if not has_numeric_data:
        logger.debug("[TABLE] No numeric data found in table")
        return False
        
    # Check for consistent column count
    col_count = len(header_row)
    for row in table_data[1:]:
        if len(row) != col_count:
            logger.debug(f"[TABLE] Inconsistent column count: expected {col_count}, got {len(row)}")
            return False
            
    return True

def parse_summary_table_with_changes(table_data):
    """Parse a summary table with year columns and change columns for products/regions."""
    if not table_data or len(table_data) < 2:
        return []
    header = [str(cell).strip() for cell in table_data[0]]
    logger.debug(f"[FALLBACK] Parsing summary table with header: {header}")
    # Identify year columns and change columns
    year_pattern = r'20\d{2}'
    year_cols = []
    change_cols = []
    for i, col in enumerate(header):
        if re.fullmatch(year_pattern, col):
            year_cols.append((i, col))
        elif 'change' in col.lower():
            change_cols.append(i)
    # Map change columns to the year they follow (assume format: year, change, year, change, ...)
    change_map = {}
    for idx, (y_idx, y_col) in enumerate(year_cols):
        if y_idx + 1 < len(header) and (y_idx + 1) in change_cols:
            change_map[y_col] = y_idx + 1
    results = []
    for row in table_data[1:]:
        if not row or not isinstance(row[0], str):
            continue
        label = row[0].strip()
        if not label or label.lower().startswith('total'):
            continue
        values = {}
        for y_idx, y_col in year_cols:
            val = row[y_idx] if y_idx < len(row) else None
            entry = {}
            if isinstance(val, (int, float)):
                entry['value'] = val
            elif isinstance(val, str):
                val_clean = val.replace('$', '').replace(',', '').strip()
                if val_clean:
                    try:
                        entry['value'] = float(val_clean)
                    except Exception:
                        pass
            c_idx = change_map.get(y_col)
            if c_idx is not None and c_idx < len(row):
                change_val = row[c_idx]
                if isinstance(change_val, (int, float)):
                    entry['change'] = change_val
                elif isinstance(change_val, str):
                    change_clean = change_val.replace('%', '').replace('(', '-').replace(')', '').replace(' ', '').strip()
                    try:
                        entry['change'] = float(change_clean)
                    except Exception:
                        pass
            if entry:
                values[y_col] = entry
        if values:
            results.append({'product': label, 'values': values})
    if results:
        logger.debug(f"[FALLBACK] Parsed summary table sample: {results[:2]}")
    return results

def find_mda_section(soup):
    """Find the MD&A section in the document."""
    mda_patterns = [
        "Management's Discussion and Analysis",
        "MD&A",
        "Management Discussion and Analysis",
        "Management's Discussion and Analysis of Financial Condition and Results of Operations"
    ]
    
    for pattern in mda_patterns:
        # Look for headers containing MD&A text
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'], 
                              string=lambda x: x and pattern.lower() in x.lower())
        if headers:
            logger.debug(f"[MD&A] Found MD&A section with pattern: {pattern}")
            return headers[0]  # Return the first matching header
    return None

def extract_notes_from_html(soup, mode='robust'):
    notes = {}
    start_time = time.time()
    # Try prioritized section headers for Revenue
    revenue_tables = []
    checked_headers = set()
    for header in REVENUE_SECTION_HEADERS:
        norm_header = normalize_header(header)
        if norm_header in checked_headers:
            continue
        checked_headers.add(norm_header)
        revenue_tables = extract_tables_after_note(soup, header)
        if revenue_tables:
            notes["Revenue"] = revenue_tables
            break
    # Try prioritized section headers for Segment/Geographic
    segment_tables = []
    checked_headers = set()
    for header in SEGMENT_SECTION_HEADERS:
        norm_header = normalize_header(header)
        if norm_header in checked_headers:
            continue
        checked_headers.add(norm_header)
        segment_tables = extract_tables_after_note(soup, header)
        if segment_tables:
            notes["Segment Information and Geographic Data"] = segment_tables
            break
    # Fallback: scan all tables for likely headers if not found
    if not notes.get("Revenue"):
        product_keywords = ["net sales by category", "net sales by product", "products and services performance"]
        product_labels = ["iphone", "mac", "ipad", "wearables", "services"]
        summary_table = find_summary_table_by_header(soup, product_keywords, product_labels)
        if summary_table:
            notes["Revenue"] = [summary_table]
            notes["Revenue_parsed"] = parse_summary_table_with_changes(summary_table)
    if not notes.get("Segment Information and Geographic Data"):
        region_keywords = [
            "net sales by reportable segment", "segment operating performance", "products and services performance",
            "total of net sales", "total net sales", "total sales"
        ]
        region_labels = ["americas", "europe", "greater china", "japan", "rest of asia"]
        product_labels = ["mac", "ipad", "iphone", "services", "wearables", "home and accessories"]
        summary_table = find_summary_table_by_header(soup, region_keywords, region_labels, product_labels)
        if summary_table:
            notes["Segment Information and Geographic Data"] = [summary_table]
            notes["Segment_parsed"] = parse_summary_table_with_changes(summary_table)
    logger.debug(f"[TIMER] extract_notes_from_html took {time.time() - start_time:.2f}s")
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

# Helper to filter core products/regions/metrics
CORE_PRODUCTS = [
    'iPhone', 'Mac', 'iPad', 'Wearables, Home and Accessories', 'Services'
]
CORE_REGIONS = [
    'Americas', 'Europe', 'Greater China', 'Japan', 'Rest of Asia Pacific'
]
CORE_METRICS = [
    'Net sales', 'Operating income'
]

def filter_core_products(products, include_extra):
    if include_extra:
        return products
    return [p for p in products if p['product'] in CORE_PRODUCTS]

def filter_core_regions(regions, include_extra):
    if include_extra:
        return regions
    return [r for r in regions if r['region'] in CORE_REGIONS and r['metric'] in CORE_METRICS]

def scrape_sales_data(mode='robust', include_extra=False, url=None):
    filings = []
    if url:
        logger.debug(f"[DEBUG] Using specific URL: {url}")
        filings = [{
            'url': url,
            'date': None,
            'accession': None
        }]
    else:
        # Default: get latest 10-K
        filings = get_latest_filing_urls(cik=CIK, form_type='10-K', count=1)
    for url in filings:
        try:
            html_content = get_sec_html(url['url'])
            if not html_content:
                continue
            soup = BeautifulSoup(html_content, 'html.parser')
            notes = extract_notes_from_html(soup, mode=mode)
            # Use parsed summary data if available
            note2_data = []
            if "Revenue_parsed" in notes:
                note2_data = notes["Revenue_parsed"]
            elif "Revenue" in notes:
                note2_data = aggregate_note2_periods(notes["Revenue"])
                note2_data = filter_core_products(note2_data, include_extra)
            note10_data = []
            if "Segment_parsed" in notes:
                note10_data = notes["Segment_parsed"]
            elif "Segment Information and Geographic Data" in notes:
                note10_data = aggregate_note10_periods(notes["Segment Information and Geographic Data"])
                note10_data = filter_core_regions(note10_data, include_extra)
            filing = {
                "date": url['date'],
                "accession": url['accession'],
                "form_type": '10-K',
                "note2 - Revenue": {"Products": note2_data},
                "note10 - Regions": note10_data,
                "url": url['url']
            }
            filings.append(filing)
        except Exception as e:
            logger.debug(f"Error processing {url}: {str(e)}")
            continue
    filings.sort(key=lambda x: x["date"], reverse=True)
    with open(OUTPUT_JSON, 'w') as f:
        json.dump({"filings": filings}, f, indent=2)
    return filings

if __name__ == '__main__':
    parser = get_arg_parser()
    args = parser.parse_args()
    scrape_sales_data(mode=args.mode, include_extra=args.include_extra, url=args.url)

# USAGE:
# python3 scrape_sec_sales.py --mode fast --include-extra
# python3 scrape_sec_sales.py --mode robust 