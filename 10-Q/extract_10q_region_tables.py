import requests
from bs4 import BeautifulSoup
import json
import re
import argparse
from pathlib import Path

def clean_label(label):
    label = re.sub(r'[:\s]*$', '', re.sub(r'\s*\([0-9]+\)$', '', label)).strip()
    label = re.sub(r'[^a-zA-Z0-9 ]', '', label)
    label = re.sub(r'\s+', ' ', label)
    return label.strip().lower()

def is_numeric(val):
    if val is None:
        return False
    val = str(val).replace(',', '').replace('$', '').strip()
    return re.match(r'^-?\d+(\.\d+)?$', val) is not None

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

def extract_table_data(table):
    rows = []
    for tr in table.find_all('tr'):
        row = []
        for td in tr.find_all(['td', 'th'], recursive=False):
            ix = td.find(['ix:nonfraction', 'ix:nonnumeric'])
            if ix:
                text = ix.get_text(strip=True)
            else:
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

def find_relevant_region_table(soup):
    region_keywords = ["americas", "europe", "greater china", "japan", "rest of asia pacific"]
    for container in soup.find_all(['ix:continuation', 'ix:nonnumeric', 'div']):
        for table in container.find_all('table'):
            table_text = table.get_text(separator=' ', strip=True).lower()
            if any(region in table_text for region in region_keywords):
                return table
    return None

def tidy_segment_operating_table(table_data):
    if not table_data or len(table_data) < 3:
        return []
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
        if not row or not isinstance(row[0], str):
            continue
        label = clean_label(row[0].strip())
        if not label:
            continue
        if any(region in label for region in valid_regions):
            current_region = row[0].strip()
            continue
        if current_region and label == "net sales":
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

def main():
    parser = argparse.ArgumentParser(description="Apple 10-Q Region Table Extractor")
    parser.add_argument('--url', type=str, required=True, help='SEC 10-Q filing URL to process')
    parser.add_argument('--output', type=str, default='10q_region_data.json', help='Output JSON file')
    args = parser.parse_args()
    resp = requests.get(args.url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'lxml')
    table = find_relevant_region_table(soup)
    if not table:
        print("No region table found.")
        return
    table_data = extract_table_data(table)
    region_data = tidy_segment_operating_table(table_data)
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