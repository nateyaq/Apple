import json
import re
from collections import defaultdict
from datetime import datetime

# Load the JSON file
with open('apple_sec_dashboard_data.json', 'r') as f:
    data = json.load(f)

issues = []
current_year = datetime.now().year

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
        seen_periods = set()
        for entry in meta['data']:
            start = entry.get('start')
            end = entry.get('end')
            if not check_date_format(str(start)):
                issues.append(f"Inconsistent date format in {metric} start: {start}")
            if not check_date_format(str(end)):
                issues.append(f"Inconsistent date format in {metric} end: {end}")
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