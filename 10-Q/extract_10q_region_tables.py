import requests
from bs4 import BeautifulSoup
import json
import re
import argparse
from pathlib import Path

HEADERS = {'User-Agent': "apple-dashboard@example.com"}

# --- Table Extraction ---
def find_section_table(soup, section_title):
    header_tags = soup.find_all(['b', 'strong', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'], string=True)
    print('[DEBUG] All section headers:')
    for tag in header_tags:
        print('  -', tag.get_text(strip=True))
    for tag in header_tags:
        if section_title.lower() in tag.get_text(strip=True).lower():
            print(f'[DEBUG] Matched section header: {tag.get_text(strip=True)}')
            next_table = tag.find_next('table')
            if next_table:
                print('[DEBUG] Found table after header. First 3 rows:')
                rows = []
                for i, tr in enumerate(next_table.find_all('tr')):
                    if i >= 3:
                        break
                    row = [td.get_text(separator=' ', strip=True) for td in tr.find_all(['td', 'th'], recursive=False)]
                    print('   ', row)
                return next_table
    print('[DEBUG] No matching section header found for:', section_title)
    return None

def extract_table_data(table):
    rows = []
    for tr in table.find_all('tr'):
        row = []
        for td in tr.find_all(['td', 'th'], recursive=False):
            text = td.get_text(separator=' ', strip=True)
            text = text.replace('\xa0', '')
            colspan = int(td.get('colspan', 1))
            if colspan > 1:
                row.extend([text] * colspan)
            else:
                row.append(text)
        if row:
            rows.append(row)
    return rows

def clean_number(val):
    if isinstance(val, (int, float)):
        return val
    if not isinstance(val, str):
        return None
    val = val.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').replace('%', '').strip()
    try:
        return float(val)
    except Exception:
        return None

def clean_label(label):
    return re.sub(r'\s*\([0-9]+\)$', '', label).strip()

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

def find_header_row(table_data):
    for i, row in enumerate(table_data):
        if len(row) > 1 and any(str(cell).strip() for cell in row[1:]):
            return i, row
    return 0, table_data[0] if table_data else []

def tidy_segment_operating_table(table_data):
    if not table_data or len(table_data) < 2:
        return []
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
                net_sales = None
                if col_idx + 1 < len(found_row):
                    val = found_row[col_idx + 1]
                    if val == '$' and col_idx + 2 < len(found_row):
                        val = found_row[col_idx + 2]
                        net_sales = clean_number(val)
                    else:
                        net_sales = clean_number(val)
                if net_sales is not None:
                    record = {
                        "type": row_type,
                        "region": label,
                        "year": year,
                        "net_sales": net_sales
                    }
                    tidy_rows.append(record)
    return tidy_rows

# New function to extract region data from the actual table structure

def extract_region_data_from_table(table_data):
    # Find the header row with region names
    header_row_idx = None
    for i, row in enumerate(table_data):
        if any('Americas' in cell for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        print('[DEBUG] No region header row found.')
        return []
    header_row = table_data[header_row_idx]
    # The period row is usually 2 rows above the region row
    period_row = table_data[header_row_idx-2] if header_row_idx >= 2 else table_data[0]
    date_row = table_data[header_row_idx-1] if header_row_idx >= 1 else table_data[0]
    # Build a map of column index to period label (date)
    col_period_map = {}
    last_period = None
    for idx, val in enumerate(period_row):
        if 'ended' in val.lower():
            last_period = val.strip()
        if re.match(r'\w+ \d{1,2}, \d{4}', val):
            col_period_map[idx] = val.strip()
        elif re.match(r'\w+ \d{1,2}, \d{4}', date_row[idx]):
            col_period_map[idx] = date_row[idx].strip()
    # Now extract region rows
    regions = ['Americas', 'Europe', 'Greater China', 'Japan', 'Rest of Asia Pacific', 'Total net sales']
    region_data = []
    for row in table_data[header_row_idx:]:
        if not row or not isinstance(row[0], str):
            continue
        region = row[0].strip()
        if region not in regions:
            continue
        row_type = 'total' if region == 'Total net sales' else 'region'
        for idx, val in enumerate(row):
            if idx == 0:
                continue
            period = col_period_map.get(idx)
            if not period:
                continue
            net_sales = clean_number(val)
            # Only include valid, non-duplicate, non-spurious values
            if net_sales is not None and net_sales != 0 and not (isinstance(net_sales, float) and abs(net_sales) < 1e-6):
                # Only add one entry per region/period
                if not any(d['region'] == region and d['period'] == period for d in region_data):
                    region_data.append({
                        'type': row_type,
                        'region': region,
                        'period': period,
                        'net_sales': net_sales
                    })
    return region_data

def main():
    parser = argparse.ArgumentParser(description="Apple 10-Q Region Table Extractor")
    parser.add_argument('--url', type=str, required=True, help='SEC 10-Q filing URL to process')
    parser.add_argument('--output', type=str, default='10q_region_data.json', help='Output JSON file')
    args = parser.parse_args()
    resp = requests.get(args.url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    # Use the actual header for region table
    table = find_section_table(soup, 'The following table shows net sales by reportable segment')
    if not table:
        print("No region table found.")
        return
    table_data = extract_table_data(table)
    region_data = extract_region_data_from_table(table_data)
    out = [{
        'url': args.url,
        'region_operating': region_data
    }]
    out_path = Path(__file__).parent / args.output
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"Saved region data to {out_path}")

if __name__ == '__main__':
    main() 