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

def extract_note2_table_text(html):
    soup = BeautifulSoup(html, 'lxml')
    tables = extract_tables_after_note(soup, 'Note 2 – Net Sales by Product Line')
    return tables

def extract_note10_table_text(html):
    soup = BeautifulSoup(html, 'lxml')
    tables = extract_tables_after_note(soup, 'Note 10 – Segment Information')
    return tables

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
def parse_note2_periods(table):
    """Parse periods from Note 2 table, mapping each product to all period/date columns, including Three, Six, Nine, Twelve Months Ended, etc."""
    allowed_products = [
        'iphone', 'mac', 'ipad', 'wearables, home and accessories', 'services',
        'wearables', 'home and accessories', 'accessories', 'other products', 'other services'
    ]
    # Add iPhone-specific patterns to catch variations
    iphone_patterns = [
        r'iphone',
        r'iphones',
        r'iphone\s+revenue',
        r'iphone\s+sales',
        r'iphone\s+net\s+sales',
        r'iphone\s+product',
        r'iphone\s+segment'
    ]
    product_map = {}
    header_row_idx = None
    # Find the first header row with period/date columns
    for i, row in enumerate(table):
        if any(re.search(r'(Three|Six|Nine|Twelve) Months Ended', str(cell)) or re.search(r'Year Ended', str(cell)) or re.search(r'Fiscal', str(cell)) for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        for i, row in enumerate(table):
            if any(re.search(r'\d{4}', str(cell)) for cell in row):
                header_row_idx = i
                break
    if header_row_idx is None:
        return []
    # Try to find a super-header row (with period type) above the header row
    header_rows = []
    for j in range(max(0, header_row_idx-2), header_row_idx+1):
        header_rows.append(table[j])
    header_rows = [row for row in header_rows if any(str(cell).strip() for cell in row)]
    if len(header_rows) >= 2:
        period_type_row = header_rows[-2]
        date_row = header_rows[-1]
    else:
        period_type_row = None
        date_row = header_rows[-1]
    # Build period labels by combining period type and date row
    period_labels = []
    for i, cell in enumerate(date_row):
        date_label = str(cell).strip()
        if period_type_row and i < len(period_type_row):
            type_label = str(period_type_row[i]).strip()
            if type_label and date_label:
                period_labels.append(f"{type_label} {date_label}".strip())
            elif date_label:
                period_labels.append(date_label)
            elif type_label:
                period_labels.append(type_label)
            else:
                period_labels.append("")
        elif date_label:
            period_labels.append(date_label)
        else:
            period_labels.append("")
    logging.debug(f"[Note2] period_labels: {period_labels}")
    # Identify which columns are period columns
    period_col_indices = []
    for i, label in enumerate(period_labels):
        if re.search(r'(Three|Six|Nine|Twelve) Months Ended', label) or re.search(r'Year Ended', label) or re.search(r'Fiscal', label) or re.search(r'\d{4}', label):
            period_col_indices.append(i)
    # Now parse each product row
    for row in table[header_row_idx+1:]:
        if not row or not any(row):
            continue
        product = str(row[0]).strip()
        # Robust normalization: remove all non-alphanumeric characters
        product_lc = re.sub(r'[^a-z0-9]', '', product.lower())
        logging.debug(f"[Note2] Product row: raw='{product}' normalized='{product_lc}'")
        matched = None
        
        # First check for iPhone using patterns
        for pattern in iphone_patterns:
            if re.search(pattern, product_lc, re.IGNORECASE):
                matched = 'iPhone'
                logging.debug(f"[Note2] Matched iPhone using pattern: {pattern}")
                break
        
        # If no iPhone match, try other products
        if not matched:
            for allowed in allowed_products:
                allowed_norm = re.sub(r'[^a-z0-9]', '', allowed.lower())
                if allowed_norm in product_lc:
                    matched = allowed.title() if allowed != 'wearables, home and accessories' else 'Wearables, Home and Accessories'
                    break
        
        # Final fallback: if 'iphone' is in the normalized product string, treat as 'iPhone'
        if not matched and 'iphone' in product_lc:
            matched = 'iPhone'
            logging.debug(f"[Note2] Matched iPhone using fallback")
            
        if not matched:
            logging.debug(f"[Note2] Skipping product row: {product}")
            continue
            
        if matched not in product_map:
            product_map[matched] = {}
        # After matching a product row
        # Extract all numeric values from the row (skip non-numeric, $, %, etc.)
        numeric_values = []
        for cell in row:
            try:
                clean_cell = re.sub(r'[^0-9.\-]', '', str(cell))
                if clean_cell and re.match(r'^-?\d+(\.\d+)?$', clean_cell):
                    numeric_values.append(float(clean_cell))
            except Exception:
                continue
        # Map numeric values to period labels in order
        for i, label in enumerate(period_labels):
            if i < len(numeric_values) and label:
                product_map[matched][label] = {"value": numeric_values[i]}
                logging.debug(f"[Note2] {matched} - {label}: {numeric_values[i]}")
    periods = []
    for product, values in product_map.items():
        if values:
            periods.append({
                "product": product,
                "values": values
            })
    return periods

def parse_note10_periods(table):
    """Parse periods from Note 10 table, robustly extracting all region/territory rows and their associated period columns."""
    periods = []
    # Find header row
    header_row = None
    header_idx = None
    for i, row in enumerate(table):
        if any(re.search(r'(Three|Six|Nine|Twelve) Months Ended', str(cell)) or re.search(r'Year Ended', str(cell)) or re.search(r'Fiscal', str(cell)) for cell in row):
            header_row = row
            header_idx = i
            break
    if not header_row:
        for i, row in enumerate(table):
            if any(re.search(r'\d{4}', str(cell)) for cell in row):
                header_row = row
                header_idx = i
                break
    if not header_row:
        return periods

    # Try to find a super-header row (with period type) above the header row
    header_rows = []
    for j in range(max(0, header_idx-2), header_idx+1):
        header_rows.append(table[j])
    header_rows = [row for row in header_rows if any(str(cell).strip() for cell in row)]
    if len(header_rows) >= 2:
        period_type_row = header_rows[-2]
        date_row = header_rows[-1]
    else:
        period_type_row = None
        date_row = header_rows[-1]

    # Build period labels by combining period type and date row
    period_labels = []
    for i, cell in enumerate(date_row):
        date_label = str(cell).strip()
        if period_type_row and i < len(period_type_row):
            type_label = str(period_type_row[i]).strip()
            if type_label and date_label:
                period_labels.append(f"{type_label} {date_label}".strip())
            elif date_label:
                period_labels.append(date_label)
            elif type_label:
                period_labels.append(type_label)
            else:
                period_labels.append("")
        elif date_label:
            period_labels.append(date_label)
        else:
            period_labels.append("")
    logging.debug(f"[Note10] period_labels: {period_labels}")

    # Define region patterns
    region_patterns = [
        r'Americas',
        r'Europe',
        r'Greater China',
        r'Japan',
        r'Rest of Asia Pacific',
        r'Asia Pacific',
        r'China',
        r'Other'
    ]

    # Define metric patterns
    metric_patterns = [
        r'Net sales',
        r'Net revenue',
        r'Revenue',
        r'Operating income',
        r'Operating profit',
        r'Income before provision for income taxes',
        r'Income before taxes'
    ]

    # Process each row after the header
    current_region = None
    current_metric = None
    for row in table[header_idx+1:]:
        if not row or not any(row):
            continue

        # Get the first cell's text
        first_cell = str(row[0]).strip()
        cell_text = first_cell.lower()
        
        # Check for region headers
        for pattern in region_patterns:
            if re.search(pattern, cell_text, re.IGNORECASE):
                current_region = pattern
                current_metric = None  # Reset metric when new region is found
                break

        # Check for metrics
        if current_region:
            for pattern in metric_patterns:
                if re.search(pattern, cell_text, re.IGNORECASE):
                    current_metric = pattern
                    values = {}
                    for i, label in enumerate(period_labels):
                        if i < len(row):
                            try:
                                value = float(str(row[i]).replace('$', '').replace(',', '').strip())
                                values[label] = {"value": value}
                                logging.debug(f"[Note10] {current_region} - {current_metric} - {label}: {value}")
                            except (ValueError, TypeError):
                                continue
                    if values:
                        periods.append({
                            "region": current_region,
                            "metric": current_metric,
                            "values": values
                        })
                    break
            # If no metric found but we have a current region and metric, try to extract values
            if current_metric and any(re.search(r'\$[\d,]+', str(cell)) for cell in row):
                values = {}
                for i, label in enumerate(period_labels):
                    if i < len(row):
                        try:
                            value = float(str(row[i]).replace('$', '').replace(',', '').strip())
                            values[label] = {"value": value}
                            logging.debug(f"[Note10] {current_region} - {current_metric} - {label}: {value}")
                        except (ValueError, TypeError):
                            continue
                if values:
                    periods.append({
                        "region": current_region,
                        "metric": current_metric,
                        "values": values
                    })

    if not periods:
        # Fallback: try to parse the first row/cell as raw text using regex
        if len(table) > 0 and len(table[0]) > 0:
            raw_text = str(table[0][0])
            # Example pattern: Americas:Net sales$124,556 $116,914 $112,093 Operating income$37,722 $35,099 $34,864
            region_regex = r'(Americas|Europe|Greater China|Japan|Rest of Asia Pacific|Asia Pacific|China|Other):'
            metric_regex = r'(Net sales|Net revenue|Revenue|Operating income|Operating profit|Income before provision for income taxes|Income before taxes)\$([\d,]+(?:\s*\$[\d,]+)*)'
            for region_match in re.finditer(region_regex, raw_text):
                region = region_match.group(1)
                region_start = region_match.end()
                # Find the next region or end of string
                next_region_match = re.search(region_regex, raw_text[region_start:])
                region_end = region_start + next_region_match.start() if next_region_match else len(raw_text)
                region_text = raw_text[region_start:region_end]
                for metric_match in re.finditer(metric_regex, region_text):
                    metric = metric_match.group(1)
                    values_str = metric_match.group(2)
                    # Extract all values
                    values = [float(v.replace(',', '')) for v in re.findall(r'\$([\d,]+)', '$'+values_str)]
                    # Assign period labels if possible, otherwise use index
                    value_dict = {}
                    for idx, value in enumerate(values):
                        label = f"Period {idx+1}"
                        value_dict[label] = {"value": value}
                    if value_dict:
                        periods.append({
                            "region": region,
                            "metric": metric,
                            "values": value_dict
                        })
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
    """Extract Note 2 and Note 10 data from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract Note 2 data
    note2_data = extract_note2_data(html_content)
    
    # Extract Note 10 data
    note10_data = extract_note10_data(html_content)
    
    return {
        'note2': note2_data,
        'note10': note10_data
    }

def aggregate_note2_periods(note2_tables):
    """Aggregate all period values for each product across all tables into a single entry per product."""
    allowed_products = [
        'iphone',
        'mac',
        'ipad',
        'wearables, home and accessories',
        'services',
    ]
    product_map = {}
    for t in note2_tables:
        table_periods = parse_note2_periods(t)
        for entry in table_periods:
            product = entry['product']
            values = entry['values']
            if product not in product_map:
                product_map[product] = {}
            for k, v in values.items():
                product_map[product][k] = v
    periods = []
    for product, values in product_map.items():
        # Only include products in allowed_products (case-insensitive)
        if values and product.lower() in allowed_products:
            periods.append({
                "product": product,
                "values": values
            })
    return periods

def scrape_sales_data():
    filings = []

    # Annual (10-K)
    for filing in get_latest_filing_urls(CIK, '10-K', 5):
        print(f"\nProcessing annual filing: {filing['date']}")
        html = get_sec_html(filing['url'])
        soup = BeautifulSoup(html, 'lxml')
        filing_text = soup.get_text(" ", strip=True)
        form_type = extract_form_type(filing_text)
        note2_tables = extract_note2_table_text(html)
        note10_tables = extract_note10_table_text(html)
        note2 = aggregate_note2_periods(note2_tables) if note2_tables else []
        note10 = []
        if note10_tables:
            for table in note10_tables:
                note10.extend(parse_note10_periods(table))
        filings.append({
            'date': filing['date'],
            'accession': filing['accession'],
            'form_type': form_type,
            'note2': note2,
            'note10': note10,
            'url': filing['url']
        })
    # Quarterly (10-Q)
    for filing in get_latest_filing_urls(CIK, '10-Q', 5):
        print(f"\nProcessing quarterly filing: {filing['date']}")
        html = get_sec_html(filing['url'])
        soup = BeautifulSoup(html, 'lxml')
        filing_text = soup.get_text(" ", strip=True)
        form_type = extract_form_type(filing_text)
        note2_tables = extract_note2_table_text(html)
        note10_tables = extract_note10_table_text(html)
        note2 = aggregate_note2_periods(note2_tables) if note2_tables else []
        note10 = []
        if note10_tables:
            for table in note10_tables:
                note10.extend(parse_note10_periods(table))
        filings.append({
            'date': filing['date'],
            'accession': filing['accession'],
            'form_type': form_type,
            'note2': note2,
            'note10': note10,
            'url': filing['url']
        })
    output = {'filings': filings}
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nExtracted sales data for last 5 years (annual) and last 5 quarters (quarterly) saved to {OUTPUT_JSON}")

def main():
    scrape_sales_data()

if __name__ == '__main__':
    main() 