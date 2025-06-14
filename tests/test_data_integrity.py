import pytest
import json
import pandas as pd

def test_sec_data_load():
    with open('./apple_sec_dashboard_data.json') as f:
        data = json.load(f)
    assert 'summary_metrics' in data
    assert isinstance(data['summary_metrics'], dict)


def test_dataframe_integrity():
    # Example: load a CSV or construct DataFrame from SEC data
    df = pd.DataFrame([
        {'metric': 'revenue', 'value': 100},
        {'metric': 'net_income', 'value': 50},
    ])
    assert not df.empty
    assert 'metric' in df.columns
    assert 'value' in df.columns


def test_dashboard_data_matches():
    # Example: check that dashboard data matches expected values
    with open('./apple_sec_dashboard_data.json') as f:
        data = json.load(f)
    # Replace with real checks
    assert data['summary_metrics']['revenue']['latest_value'] > 0 