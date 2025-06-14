import json
import re
from collections import defaultdict
from datetime import datetime

# Load the JSON file
with open('apple_sec_dashboard_data.json', 'r') as f:
    data = json.load(f)

issues = []
current_year = datetime.now().year

# Define balance sheet metrics
BALANCE_SHEET_METRICS = {
    'total_assets': 'Total Assets',
    'cash_and_equivalents': 'Cash and Cash Equivalents',
    'shareholders_equity': 'Shareholders Equity'
}

def check_type_consistency(section, key, expected_type):
    values = []
    for metric, v in section.items():
        val = v.get(key)
        if val is not None:
            values.append(type(val))
            if not isinstance(val, expected_type):
                issues.append(f"Type inconsistency in {metric}.{key}: {val} ({type(val)})")
    return values

def check_negative_values(section, key):
    for metric, v in section.items():
        val = v.get(key)
        if val is not None:
            try:
                if float(val) < 0:
                    issues.append(f"Negative value in {metric}.{key}: {val}")
            except Exception:
                pass

def check_date_format(date_str):
    # Accepts 'YYYY-MM-DD' or 'YYYY-MM-DD 00:00:00'
    if not re.match(r"^\d{4}-\d{2}-\d{2}( 00:00:00)?$", date_str):
        return False
    return True

def check_date_range(start_date, end_date, is_balance_sheet=False):
    # For balance sheet metrics, we only need to check end date
    if is_balance_sheet:
        return check_date_format(str(end_date))
    
    try:
        start = datetime.strptime(str(start_date).split()[0], '%Y-%m-%d')
        end = datetime.strptime(str(end_date).split()[0], '%Y-%m-%d')
        return start <= end
    except Exception:
        return False

def check_dates(section, key):
    for metric, v in section.items():
        val = v.get(key)
        if val is not None and not check_date_format(str(val)):
            issues.append(f"Inconsistent date format in {metric}.{key}: {val}")

def check_time_series_years(time_series):
    years = set()
    for entry in time_series:
        years.add(entry.get('year'))
    all_years = list(sorted(years))
    missing = []
    if all_years:
        for y in range(int(min(all_years)), int(max(all_years))+1):
            if y not in years:
                missing.append(y)
    if missing:
        issues.append(f"Missing years in time_series_data: {missing}")

def check_raw_metrics(raw_metrics):
    for metric, meta in raw_metrics.items():
        is_balance_sheet = metric in BALANCE_SHEET_METRICS
        seen_periods = set()
        for entry in meta['data']:
            start = entry.get('start')
            end = entry.get('end')
            
            # For balance sheet metrics, we only validate end date
            if not is_balance_sheet:
                if not check_date_format(str(start)):
                    issues.append(f"Inconsistent date format in {metric} start: {start}")
            if not check_date_format(str(end)):
                issues.append(f"Inconsistent date format in {metric} end: {end}")
            
            if not is_balance_sheet and not check_date_range(start, end):
                issues.append(f"Invalid date range in {metric}: start {start} is after end {end}")
            
            period = (start, end)
            if period in seen_periods:
                issues.append(f"Duplicate period in {metric}: {period}")
            seen_periods.add(period)
            val = entry.get('val')
            if val is not None:
                try:
                    if float(val) < 0:
                        issues.append(f"Negative value in {metric} period {period}: {val}")
                except Exception:
                    pass

def check_growth_rates(metric_data):
    for metric, meta in metric_data.items():
        if 'growth_rates' not in meta:
            continue
        
        # Sort data by date for comparison
        data_points = sorted(meta['data'], key=lambda x: x['end'])
        growth_rates = meta['growth_rates']
        
        # Verify growth rates match the data
        for i in range(1, len(data_points)):
            prev_val = float(data_points[i-1]['val'])
            curr_val = float(data_points[i]['val'])
            if prev_val == 0:
                continue
            expected_growth = ((curr_val - prev_val) / prev_val) * 100
            actual_growth = growth_rates[i-1]['growth_rate']
            
            # Allow for small floating point differences
            if abs(expected_growth - actual_growth) > 0.01:
                issues.append(f"Inconsistent growth rate in {metric}: expected {expected_growth:.2f}%, got {actual_growth:.2f}%")

def check_future_years():
    # Check summary_metrics
    for metric, v in data.get('summary_metrics', {}).items():
        year = v.get('latest_year')
        if year is not None and float(year) > current_year:
            issues.append(f"Future year in summary_metrics.{metric}: {year}")
    # Check quarterly_metrics
    for metric, v in data.get('quarterly_metrics', {}).items():
        for key in ['latest_quarterly_period', 'latest_annual_period']:
            period = v.get(key)
            if period:
                try:
                    y = int(str(period)[:4])
                    if y > current_year:
                        issues.append(f"Future year in quarterly_metrics.{metric}.{key}: {period}")
                except Exception:
                    pass
        for key in ['latest_quarterly_value', 'latest_annual_value']:
            year = v.get(key)
            if year is not None and isinstance(year, (int, float)) and year > current_year:
                issues.append(f"Future year in quarterly_metrics.{metric}.{key}: {year}")
    # Check time_series_data
    for entry in data.get('time_series_data', []):
        year = entry.get('year')
        if year is not None and float(year) > current_year:
            issues.append(f"Future year in time_series_data: {year}")
    # Check raw_metrics
    for metric, meta in data.get('raw_metrics', {}).items():
        for entry in meta.get('data', []):
            fy = entry.get('fy')
            if fy is not None and float(fy) > current_year:
                issues.append(f"Future year in raw_metrics.{metric}.data: {fy}")
        for entry in meta.get('annual_data', []):
            fy = entry.get('fy')
            if fy is not None and float(fy) > current_year:
                issues.append(f"Future year in raw_metrics.{metric}.annual_data: {fy}")
        for entry in meta.get('quarterly_data', []):
            fy = entry.get('fy')
            if fy is not None and float(fy) > current_year:
                issues.append(f"Future year in raw_metrics.{metric}.quarterly_data: {fy}")

def check_year_type():
    # Check summary_metrics
    for metric, v in data.get('summary_metrics', {}).items():
        year = v.get('latest_year')
        if year is not None and not isinstance(year, int):
            issues.append(f"Non-integer year in summary_metrics.{metric}: {year} ({type(year)})")
    # Check quarterly_metrics (only check *_period fields for year type, not *_value fields)
    for metric, v in data.get('quarterly_metrics', {}).items():
        for key in ['latest_quarterly_period', 'latest_annual_period']:
            period = v.get(key)
            if period:
                try:
                    y = int(str(period)[:4])
                    if not isinstance(y, int):
                        issues.append(f"Non-integer year in quarterly_metrics.{metric}.{key}: {period} ({type(y)})")
                except Exception:
                    pass
        # Do NOT check *_value fields here (they are amounts, not years)
    # Check time_series_data
    for entry in data.get('time_series_data', []):
        year = entry.get('year')
        if year is not None and not isinstance(year, int):
            issues.append(f"Non-integer year in time_series_data: {year} ({type(year)})")
    # Check raw_metrics
    for metric, meta in data.get('raw_metrics', {}).items():
        for entry in meta.get('data', []):
            fy = entry.get('fy')
            if fy is not None and not isinstance(fy, int):
                issues.append(f"Non-integer year in raw_metrics.{metric}.data: {fy} ({type(fy)})")
        for entry in meta.get('annual_data', []):
            fy = entry.get('fy')
            if fy is not None and not isinstance(fy, int):
                issues.append(f"Non-integer year in raw_metrics.{metric}.annual_data: {fy} ({type(fy)})")
        for entry in meta.get('quarterly_data', []):
            fy = entry.get('fy')
            if fy is not None and not isinstance(fy, int):
                issues.append(f"Non-integer year in raw_metrics.{metric}.quarterly_data: {fy} ({type(fy)})")

def check_annual_quarterly_consistency(raw_metrics):
    for metric, meta in raw_metrics.items():
        is_balance_sheet = metric in BALANCE_SHEET_METRICS
        if is_balance_sheet:
            continue  # Skip consistency check for balance sheet metrics
            
        annual_data = {entry['end']: entry['val'] for entry in meta.get('annual_data', [])}
        quarterly_data = meta.get('quarterly_data', [])
        
        # Group quarterly data by fiscal year
        quarterly_by_year = defaultdict(list)
        for entry in quarterly_data:
            fy = entry.get('fy')
            if fy is not None:
                quarterly_by_year[fy].append(entry)
        
        # Check if sum of quarters matches annual data
        for year, quarters in quarterly_by_year.items():
            if len(quarters) == 4:  # Only check complete years
                annual_end = None
                for entry in meta.get('annual_data', []):
                    if entry.get('fy') == year:
                        annual_end = entry['end']
                        annual_val = float(entry['val'])
                        break
                
                if annual_end:
                    quarter_sum = sum(float(q['val']) for q in quarters)
                    if abs(quarter_sum - annual_val) > 0.01:  # Allow for small floating point differences
                        issues.append(f"Inconsistent annual/quarterly data in {metric} for year {year}: "
                                    f"sum of quarters ({quarter_sum}) != annual value ({annual_val})")

def main():
    print("--- Validating summary_metrics ---")
    check_type_consistency(data['summary_metrics'], 'latest_year', (int, float, str))
    check_negative_values(data['summary_metrics'], 'latest_value')
    check_dates(data['summary_metrics'], 'latest_period')

    print("--- Validating quarterly_metrics ---")
    check_type_consistency(data['quarterly_metrics'], 'latest_quarterly_period', str)
    check_negative_values(data['quarterly_metrics'], 'latest_quarterly_value')
    check_dates(data['quarterly_metrics'], 'latest_quarterly_period')
    check_negative_values(data['quarterly_metrics'], 'latest_annual_value')
    check_dates(data['quarterly_metrics'], 'latest_annual_period')

    print("--- Validating time_series_data ---")
    check_time_series_years(data.get('time_series_data', []))

    print("--- Validating raw_metrics ---")
    check_raw_metrics(data['raw_metrics'])
    check_growth_rates(data['raw_metrics'])
    check_annual_quarterly_consistency(data['raw_metrics'])

    print("--- Checking for future years ---")
    check_future_years()

    print("--- Checking for integer year fields ---")
    check_year_type()

    print("\n--- Issues found ---")
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("No issues found. JSON structure is valid.")

if __name__ == "__main__":
    main() 