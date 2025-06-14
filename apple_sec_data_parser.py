import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
from dateutil.relativedelta import relativedelta
warnings.filterwarnings('ignore')

class AppleSECDataParser:
    def __init__(self):
        self.headers = {'User-Agent': "apple-dashboard@example.com"}
        self.cik = "0000320193"  # Apple's CIK
        self.base_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK"
        self.raw_data = None
        self.processed_data = {}
        
    def fetch_sec_data(self):
        """Fetch SEC data from the API"""
        url = f"{self.base_url}{self.cik}.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            self.raw_data = response.json()
            print(f"Successfully fetched SEC data for {self.raw_data.get('entityName', 'Apple Inc.')}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching SEC data: {e}")
            return False
    
    def explore_all_metric_fields(self):
        """Debug function to explore available fields for all financial metrics"""
        if not self.raw_data:
            print("No SEC data available. Please fetch data first.")
            return
        
        metric_keywords = {
            'revenue': ['revenue', 'sales'],
            'income': ['income', 'profit', 'earnings'],
            'assets': ['assets'],
            'cash': ['cash', 'equivalents'],
            'research': ['research', 'development'],
            'equity': ['equity', 'stockholders', 'shareholders'],
            'expenses': ['expenses', 'costs']
        }
        
        try:
            us_gaap_facts = self.raw_data['facts']['us-gaap']
            
            print("\n🔍 Comprehensive Field Analysis:")
            for category, keywords in metric_keywords.items():
                print(f"\n📊 {category.upper()} FIELDS:")
                fields_found = []
                
                for field_name, field_data in us_gaap_facts.items():
                    if any(keyword.lower() in field_name.lower() for keyword in keywords):
                        if 'units' in field_data and 'USD' in field_data['units']:
                            df = pd.DataFrame(field_data['units']['USD'])
                            annual_data = df[df['form'] == '10-K'] if len(df) > 0 else pd.DataFrame()
                            if len(annual_data) > 0:
                                latest_year = annual_data['fy'].max()
                                data_count = len(annual_data)
                                fields_found.append({
                                    'field': field_name,
                                    'latest_year': latest_year,
                                    'count': data_count
                                })
                
                # Sort by latest year and data count
                fields_found.sort(key=lambda x: (x['latest_year'], x['count']), reverse=True)
                
                for field in fields_found[:8]:  # Show top 8 fields per category
                    print(f"  {field['field']}: {field['latest_year']} ({field['count']} points)")
                    
                if not fields_found:
                    print(f"  No fields found for {category}")
                    
        except Exception as e:
            print(f"Error in comprehensive field analysis: {e}")
    
    def explore_revenue_fields(self):
        """Debug function to explore available revenue-related fields"""
        if not self.raw_data:
            print("No SEC data available. Please fetch data first.")
            return
        
        try:
            us_gaap_facts = self.raw_data['facts']['us-gaap']
            revenue_fields = []
            
            # Look for any field containing 'revenue' (case insensitive)
            for field_name, field_data in us_gaap_facts.items():
                if 'revenue' in field_name.lower():
                    # Check if it has USD data and 10-K forms
                    if 'units' in field_data and 'USD' in field_data['units']:
                        df = pd.DataFrame(field_data['units']['USD'])
                        annual_data = df[df['form'] == '10-K']
                        if len(annual_data) > 0:
                            latest_year = annual_data['fy'].max()
                            revenue_fields.append({
                                'field': field_name,
                                'latest_year': latest_year,
                                'data_points': len(annual_data)
                            })
            
            print("\n🔍 Available Revenue Fields:")
            for field in sorted(revenue_fields, key=lambda x: x['latest_year'], reverse=True):
                print(f"  {field['field']}: Latest year {field['latest_year']}, {field['data_points']} annual data points")
                
            return revenue_fields
            
        except Exception as e:
            print(f"Error exploring revenue fields: {e}")
            return []
    
    def extract_financial_metric(self, metric_path, metric_name, include_quarterly=True):
        """Extract a specific financial metric from the SEC data with both annual and quarterly data"""
        try:
            # Identify balance sheet metrics (point-in-time, not period difference)
            balance_sheet_metrics = [
                'Total Assets', 'Cash and Cash Equivalents', 'Shareholders Equity',
                'Total Liabilities', 'Current Assets', 'Current Liabilities'
            ]
            is_balance_sheet = metric_name in balance_sheet_metrics
            # Navigate through the nested structure
            current_data = self.raw_data
            for key in metric_path.split('.'):
                current_data = current_data[key]
            # Extract USD values
            if 'units' in current_data and 'USD' in current_data['units']:
                df = pd.DataFrame(current_data['units']['USD'])
                print(f"\nExtracting {metric_name} from {metric_path}")
                print("Columns:", df.columns.tolist())
                print("Sample data:", df.head())
                # Check for required columns
                if 'end' not in df.columns or 'val' not in df.columns or 'form' not in df.columns:
                    print(f"[WARN] Missing required columns for {metric_name}: must have at least 'end', 'val', 'form'. Skipping this metric.")
                    return None
                if df.empty:
                    print(f"[WARN] DataFrame is empty for {metric_name}. Skipping this metric.")
                    return None
                print(f"[DEBUG] {metric_name}: DataFrame shape before deduplication: {df.shape}")
                # Filter out data points that span more than 3 months for quarterly data
                if 'start' in df.columns and 'end' in df.columns:
                    df['start'] = pd.to_datetime(df['start'], errors='coerce')
                    df['end'] = pd.to_datetime(df['end'], errors='coerce')
                    df['date_diff'] = (df['end'] - df['start']).dt.days
                    # For balance sheet, keep only 10-K/10-Q at period end (ignore date_diff)
                    if not is_balance_sheet:
                        # Only filter out data points that are explicitly marked as quarterly but span more than 4 months
                        quarterly_mask = (df['form'] == '10-Q') & (df['date_diff'] > 120)
                        df = df[~quarterly_mask]
                        print(f"[DEBUG] Filtered out {quarterly_mask.sum()} quarterly data points spanning more than 4 months")
                    df = df.drop('date_diff', axis=1)
                # Enhanced deduplication for quarterly data: prefer correct fp and frame
                if 'fp' in df.columns and 'end' in df.columns:
                    for quarter in ['Q1', 'Q2', 'Q3', 'Q4']:
                        mask = df['fp'] == quarter
                        if mask.any():
                            df.loc[mask, 'is_correct_fp'] = True
                        else:
                            df['is_correct_fp'] = False
                    if 'frame' in df.columns:
                        df['has_frame'] = df['frame'].notnull()
                    else:
                        df['has_frame'] = False
                    df = df.sort_values(by=['end', 'is_correct_fp', 'has_frame'], ascending=[True, False, False])
                    before = df.shape[0]
                    df = df.drop_duplicates(subset=['end'], keep='first')
                    after = df.shape[0]
                    print(f"[DEBUG] Enhanced deduplication: Dropped {before - after} rows by preferring correct fp and frame")
                else:
                    df['end'] = pd.to_datetime(df['end'], errors='coerce')
                    if 'frame' in df.columns:
                        df['has_frame'] = df['frame'].notnull()
                        df = df.sort_values(by=['end', 'has_frame'], ascending=[True, False])
                    else:
                        df = df.sort_values(by=['end'], ascending=[True])
                    before = df.shape[0]
                    # Only deduplicate if there are exact duplicate 'end' values
                    if df['end'].duplicated().any():
                        df = df.drop_duplicates(subset=['end'], keep='first')
                        after = df.shape[0]
                        print(f"[DEBUG] {metric_name}: Dropped {before - after} rows by deduplication (end only)")
                    else:
                        print(f"[DEBUG] {metric_name}: No duplicate 'end' values, no deduplication performed.")
                print(f"[DEBUG] {metric_name}: DataFrame shape after deduplication: {df.shape}")
                df = df.sort_values('end')
                # --- Q4 Calculation Logic ---
                # For each fiscal year, if Q1, Q2, Q3, and annual (10-K) are present but Q4 is missing, calculate Q4
                if not is_balance_sheet and 'fp' in df.columns and 'fy' in df.columns and 'val' in df.columns and 'form' in df.columns:
                    new_rows = []
                    for year in df['fy'].unique():
                        year_mask = df['fy'] == year
                        annual = df[year_mask & (df['form'] == '10-K')]
                        q1 = df[year_mask & (df['fp'] == 'Q1')]
                        q2 = df[year_mask & (df['fp'] == 'Q2')]
                        q3 = df[year_mask & (df['fp'] == 'Q3')]
                        q4 = df[year_mask & (df['fp'] == 'Q4')]
                        if not annual.empty and not q1.empty and not q2.empty and not q3.empty and q4.empty:
                            q4_val = annual.iloc[0]['val'] - (q1.iloc[0]['val'] + q2.iloc[0]['val'] + q3.iloc[0]['val'])
                            # Estimate Q4 start as Q3 end, end as annual end
                            q4_start = q3.iloc[0]['end'] if 'end' in q3.columns else None
                            q4_end = annual.iloc[0]['end'] if 'end' in annual.columns else None
                            q4_row = {col: None for col in df.columns}
                            q4_row['fy'] = year
                            q4_row['fp'] = 'Q4'
                            q4_row['form'] = '10-K'
                            q4_row['val'] = q4_val
                            if q4_start is not None:
                                q4_row['start'] = q4_start
                            if q4_end is not None:
                                q4_row['end'] = q4_end
                            # Copy over other fields from annual as appropriate
                            for col in ['accn', 'filed', 'frame']:
                                if col in df.columns and col in annual.columns:
                                    q4_row[col] = annual.iloc[0][col]
                            new_rows.append(q4_row)
                    if new_rows:
                        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                # Dynamically select columns for output
                base_cols = ['end', 'val', 'fy', 'form']
                if 'start' in df.columns:
                    output_cols = ['start'] + base_cols
                else:
                    output_cols = base_cols
                # Remove rows with NaT or NaN in 'end' (invalid dates)
                df = df[df['end'].notnull()]
                # Ensure 'end' and 'start' are datetime before formatting
                if not pd.api.types.is_datetime64_any_dtype(df['end']):
                    df['end'] = pd.to_datetime(df['end'], errors='coerce')
                df['end'] = df['end'].dt.strftime('%Y-%m-%d')
                if 'start' in df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(df['start']):
                        df['start'] = pd.to_datetime(df['start'], errors='coerce')
                    df['start'] = df['start'].dt.strftime('%Y-%m-%d')
                    # Exclude 'start' if it is None for any record
                    df = df[df['start'].notnull()]
                # Separate annual and quarterly data
                annual_data = df[df['form'] == '10-K'].copy()
                quarterly_data = df[df['form'] == '10-Q'].copy() if include_quarterly else pd.DataFrame()
                
                # --- Fallback: sum quarterly values for annual if missing (for operating_income and research_development) ---
                if metric_name in ['Operating Income', 'Research & Development']:
                    # Find all years present in quarterly data
                    if not quarterly_data.empty and 'fy' in quarterly_data.columns:
                        for year in sorted(quarterly_data['fy'].unique()):
                            # If annual_data for this year is missing
                            if annual_data.empty or year not in annual_data['fy'].values:
                                year_quarters = quarterly_data[quarterly_data['fy'] == year]
                                if len(year_quarters) == 4:
                                    # Sum the four quarters
                                    summed_val = year_quarters['val'].sum()
                                    # Use the end date of the last quarter
                                    end_date = year_quarters.sort_values('end').iloc[-1]['end']
                                    # Create a synthetic annual record
                                    annual_row = {col: None for col in annual_data.columns}
                                    annual_row['fy'] = year
                                    annual_row['form'] = '10-K'
                                    annual_row['val'] = summed_val
                                    annual_row['end'] = end_date
                                    # Optionally, add a flag or note that this is synthetic
                                    annual_data = pd.concat([annual_data, pd.DataFrame([annual_row])], ignore_index=True)
                                    annual_data = annual_data.sort_values('end')

                # Remove future-dated annual and quarterly data (apply while still DataFrame)
                from datetime import datetime
                current_year = datetime.now().year
                if not annual_data.empty and 'fy' in annual_data.columns:
                    annual_data = annual_data[annual_data['fy'] <= current_year]
                    if 'end' in annual_data.columns:
                        annual_data['end_dt'] = pd.to_datetime(annual_data['end'], errors='coerce')
                        annual_data = annual_data[annual_data['end_dt'] <= pd.Timestamp.now()]
                        annual_data = annual_data.drop(columns=['end_dt'])
                if not quarterly_data.empty and 'fy' in quarterly_data.columns:
                    quarterly_data = quarterly_data[quarterly_data['fy'] <= current_year]
                    if 'end' in quarterly_data.columns:
                        quarterly_data['end_dt'] = pd.to_datetime(quarterly_data['end'], errors='coerce')
                        quarterly_data = quarterly_data[quarterly_data['end_dt'] <= pd.Timestamp.now()]
                        quarterly_data = quarterly_data.drop(columns=['end_dt'])

                # Combine all data for comprehensive view
                all_recent_data = pd.concat([annual_data, quarterly_data]).sort_values('end')
                # Determine the most recent value (could be quarterly or annual)
                latest_entry = all_recent_data.iloc[-1] if len(all_recent_data) > 0 else None
                # Get latest quarterly and annual separately for comparison
                latest_quarterly = quarterly_data.iloc[-1] if len(quarterly_data) > 0 else None
                latest_annual = annual_data.iloc[-1] if len(annual_data) > 0 else None
                # For balance sheet metrics, drop 'start' column entirely before output
                if is_balance_sheet and 'start' in df.columns:
                    df = df.drop(columns=['start'])
                    output_cols = [col for col in output_cols if col != 'start']
                # Final filter: only keep valid SEC records for flow metrics
                def valid_flow_row(row):
                    try:
                        if 'start' in row and 'end' in row and row['start'] and row['end']:
                            s = pd.to_datetime(row['start'], errors='coerce')
                            e = pd.to_datetime(row['end'], errors='coerce')
                            if pd.isnull(s) or pd.isnull(e) or s > e:
                                return False
                        if 'val' in row and row['val'] is not None and row['val'] < 0:
                            return False
                        return True
                    except Exception:
                        return False
                if not is_balance_sheet:
                    recent_annual = annual_data.tail(10) if len(annual_data) > 0 else pd.DataFrame()
                    recent_quarterly = quarterly_data.tail(8) if len(quarterly_data) > 0 else pd.DataFrame()
                    recent_annual = recent_annual[recent_annual.apply(valid_flow_row, axis=1)]
                    recent_quarterly = recent_quarterly[recent_quarterly.apply(valid_flow_row, axis=1)]
                    # Combine all data for comprehensive view
                    all_recent_data = pd.concat([recent_annual, recent_quarterly]).sort_values('end')
                    if not is_balance_sheet:
                        all_recent_data = all_recent_data[all_recent_data.apply(valid_flow_row, axis=1)]
                # For balance sheet, annual value is the value at fiscal year end (not a difference)
                if is_balance_sheet:
                    recent_annual = annual_data.groupby('fy').last().reset_index().tail(10) if len(annual_data) > 0 else pd.DataFrame()
                else:
                    recent_annual = annual_data.tail(10) if len(annual_data) > 0 else pd.DataFrame()
                # Get recent quarterly data (last 8 quarters)
                recent_quarterly = quarterly_data.tail(8) if len(quarterly_data) > 0 else pd.DataFrame()
                # Final filter: only keep valid SEC records for flow metrics
                def valid_flow_row(row):
                    try:
                        if 'start' in row and 'end' in row and row['start'] and row['end']:
                            s = pd.to_datetime(row['start'], errors='coerce')
                            e = pd.to_datetime(row['end'], errors='coerce')
                            if pd.isnull(s) or pd.isnull(e) or s > e:
                                return False
                        if 'val' in row and row['val'] is not None and row['val'] < 0:
                            return False
                        return True
                    except Exception:
                        return False
                if not is_balance_sheet:
                    recent_annual = recent_annual[recent_annual.apply(valid_flow_row, axis=1)]
                    recent_quarterly = recent_quarterly[recent_quarterly.apply(valid_flow_row, axis=1)]
                # Combine all data for comprehensive view
                all_recent_data = pd.concat([recent_annual, recent_quarterly]).sort_values('end')
                if not is_balance_sheet:
                    all_recent_data = all_recent_data[all_recent_data.apply(valid_flow_row, axis=1)]
                # Determine the most recent value (could be quarterly or annual)
                latest_entry = all_recent_data.iloc[-1] if len(all_recent_data) > 0 else None
                # Get latest quarterly and annual separately for comparison
                latest_quarterly = recent_quarterly.iloc[-1] if len(recent_quarterly) > 0 else None
                latest_annual = recent_annual.iloc[-1] if len(recent_annual) > 0 else None
                # For balance sheet metrics, drop 'start' column entirely before output
                if is_balance_sheet and 'start' in df.columns:
                    df = df.drop(columns=['start'])
                    output_cols = [col for col in output_cols if col != 'start']
                # Convert DataFrame to records (no inferring or cleaning for flow metrics)
                data_records = all_recent_data[output_cols].to_dict('records')
                annual_records = recent_annual[output_cols].to_dict('records')
                quarterly_records = recent_quarterly[output_cols].to_dict('records')
                def safe_int(val):
                    try:
                        return int(val)
                    except Exception:
                        return val
                return {
                    'metric_name': metric_name,
                    'data': [
                        {**rec, 'fy': safe_int(rec.get('fy')) if rec.get('fy') is not None else None}
                        for rec in data_records
                    ],
                    'annual_data': [
                        {**rec, 'fy': safe_int(rec.get('fy')) if rec.get('fy') is not None else None}
                        for rec in annual_records
                    ],
                    'quarterly_data': [
                        {**rec, 'fy': safe_int(rec.get('fy')) if rec.get('fy') is not None else None}
                        for rec in quarterly_records
                    ],
                    'latest_value': latest_entry['val'] if latest_entry is not None else 0,
                    'latest_year': safe_int(latest_entry['fy']) if latest_entry is not None else None,
                    'latest_period': latest_entry['end'] if latest_entry is not None else None,
                    'latest_form': latest_entry['form'] if latest_entry is not None else None,
                    'latest_quarterly_value': latest_quarterly['val'] if latest_quarterly is not None else None,
                    'latest_quarterly_period': latest_quarterly['end'] if latest_quarterly is not None else None,
                    'latest_annual_value': latest_annual['val'] if latest_annual is not None else None,
                    'latest_annual_period': latest_annual['end'] if latest_annual is not None else None
                }
        except (KeyError, IndexError, TypeError) as e:
            print(f"Could not extract {metric_name}: {e}")
            return None
    
    def calculate_growth_rates(self, data_series):
        """Calculate year-over-year growth rates"""
        if len(data_series) < 2:
            return []
        
        growth_rates = []
        for i in range(1, len(data_series)):
            current_val = data_series[i]['val']
            previous_val = data_series[i-1]['val']
            
            if previous_val != 0:
                growth_rate = ((current_val - previous_val) / previous_val) * 100
                growth_rates.append({
                    'year': data_series[i]['fy'],
                    'growth_rate': round(growth_rate, 2)
                })
        
        return growth_rates
    
    def calculate_quarterly_vs_annual_change(self, quarterly_value, annual_value):
        """Calculate percentage change from annual to quarterly values"""
        if not quarterly_value or not annual_value or annual_value == 0:
            return 0
        return round(((quarterly_value - annual_value) / annual_value) * 100, 2)
    
    def process_all_metrics(self):
        """Process all key financial metrics for the dashboard"""
        if not self.raw_data:
            print("No SEC data available. Please fetch data first.")
            return False
        
        # Define key financial metrics to extract with comprehensive fallback paths
        metrics_config = {
            'revenue': {
                'path': 'facts.us-gaap.RevenueFromContractWithCustomerExcludingAssessedTax',
                'name': 'Total Revenue',
                'fallback_paths': [
                    'facts.us-gaap.Revenues',
                    'facts.us-gaap.SalesRevenueNet',
                    'facts.us-gaap.RevenueFromContractWithCustomerIncludingAssessedTax',
                    'facts.us-gaap.SalesRevenueGoodsNet',
                    'facts.us-gaap.RevenueFromSaleOfGoods',
                    'facts.us-gaap.SalesRevenueServicesNet'
                ]
            },
            'net_income': {
                'path': 'facts.us-gaap.NetIncomeLoss',
                'name': 'Net Income',
                'fallback_paths': [
                    'facts.us-gaap.ProfitLoss',
                    'facts.us-gaap.NetIncomeLossAvailableToCommonStockholdersBasic',
                    'facts.us-gaap.NetIncomeLossAttributableToParent',
                    'facts.us-gaap.ComprehensiveIncomeNetOfTax',
                    'facts.us-gaap.IncomeLossFromContinuingOperations'
                ]
            },
            'total_assets': {
                'path': 'facts.us-gaap.Assets',
                'name': 'Total Assets',
                'fallback_paths': [
                    'facts.us-gaap.AssetsTotal',
                    'facts.us-gaap.AssetsCurrent',
                    'facts.us-gaap.AssetsCurrentAndNoncurrent'
                ]
            },
            'cash_and_equivalents': {
                'path': 'facts.us-gaap.CashAndCashEquivalentsAtCarryingValue',
                'name': 'Cash and Cash Equivalents',
                'fallback_paths': [
                    'facts.us-gaap.CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
                    'facts.us-gaap.Cash',
                    'facts.us-gaap.CashAndShortTermInvestments',
                    'facts.us-gaap.CashEquivalentsAtCarryingValue',
                    'facts.us-gaap.CashAndCashEquivalents'
                ]
            },
            'research_development': {
                'path': 'facts.us-gaap.ResearchAndDevelopmentExpense',
                'name': 'Research & Development',
                'fallback_paths': [
                    'facts.us-gaap.ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost',
                    'facts.us-gaap.ResearchAndDevelopmentInProcess',
                    'facts.us-gaap.ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost',
                    'facts.us-gaap.ResearchAndDevelopmentAssets'
                ]
            },
            'operating_income': {
                'path': 'facts.us-gaap.OperatingIncomeLoss',
                'name': 'Operating Income',
                'fallback_paths': [
                    'facts.us-gaap.IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                    'facts.us-gaap.OperatingRevenue',
                    'facts.us-gaap.IncomeLossFromContinuingOperationsBeforeIncomeTaxes',
                    'facts.us-gaap.GrossProfit',
                    'facts.us-gaap.OperatingExpenses'
                ]
            },
            'shareholders_equity': {
                'path': 'facts.us-gaap.StockholdersEquity',
                'name': 'Shareholders Equity',
                'fallback_paths': [
                    'facts.us-gaap.StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
                    'facts.us-gaap.PartnersCapital',
                    'facts.us-gaap.MembersEquity',
                    'facts.us-gaap.StockholdersEquityAttributableToParent',
                    'facts.us-gaap.Equity'
                ]
            }
        }
        
        # Extract each metric
        for key, config in metrics_config.items():
            primary_path = config['path']
            metric_data = self.extract_financial_metric(primary_path, config['name'])
            used_path = primary_path
            
            # Try fallback paths if primary path fails
            if not metric_data and 'fallback_paths' in config:
                print(f"  Primary path failed for {config['name']}, trying fallbacks...")
                for fallback_path in config['fallback_paths']:
                    metric_data = self.extract_financial_metric(fallback_path, config['name'])
                    if metric_data:
                        used_path = fallback_path
                        print(f"  ✓ Found data using fallback: {fallback_path.split('.')[-1]}")
                        break
            
            if metric_data:
                # Calculate growth rates
                growth_rates = self.calculate_growth_rates(metric_data['data'])
                metric_data['growth_rates'] = growth_rates
                metric_data['source_field'] = used_path.split('.')[-1]  # Store which field was used
                
                self.processed_data[key] = metric_data
                if used_path == primary_path:
                    print(f"✓ Processed {config['name']}")
                else:
                    print(f"✓ Processed {config['name']} (using fallback)")
            else:
                print(f"✗ Could not process {config['name']} - no data found in any field")
        
        return True
    
    def generate_dashboard_data(self):
        """Generate structured data for the dashboard"""
        if not self.processed_data:
            print("No processed data available. Please process metrics first.")
            return None
        
        # Prepare summary metrics with both quarterly and annual data
        summary_metrics = {}
        quarterly_metrics = {}
        
        for key, data in self.processed_data.items():
            # Annual metrics (primary display)
            summary_metrics[key] = {
                'name': data['metric_name'],
                'latest_value': data['latest_value'],
                'latest_year': data['latest_year'],
                'latest_period': data.get('latest_period'),
                'latest_form': data.get('latest_form'),
                'growth_rate': data['growth_rates'][-1]['growth_rate'] if data['growth_rates'] else 0
            }
            
            # Quarterly metrics for comparison
            if data.get('latest_quarterly_value'):
                quarterly_metrics[key] = {
                    'name': data['metric_name'],
                    'latest_quarterly_value': data['latest_quarterly_value'],
                    'latest_quarterly_period': data.get('latest_quarterly_period'),
                    'latest_annual_value': data.get('latest_annual_value'),
                    'latest_annual_period': data.get('latest_annual_period'),
                    'quarterly_vs_annual_change': self.calculate_quarterly_vs_annual_change(
                        data.get('latest_quarterly_value'), 
                        data.get('latest_annual_value')
                    )
                }
        
        # Prepare time series data for charts
        time_series_data = []
        if 'revenue' in self.processed_data and 'net_income' in self.processed_data:
            revenue_data = {item['fy']: item['val'] for item in self.processed_data['revenue']['data']}
            income_data = {item['fy']: item['val'] for item in self.processed_data['net_income']['data']}
            
            # Combine data by year
            years = sorted(set(revenue_data.keys()) & set(income_data.keys()))
            for year in years:
                time_series_data.append({
                    'year': year,
                    'revenue': revenue_data.get(year, 0) / 1000000000,  # Convert to billions
                    'net_income': income_data.get(year, 0) / 1000000000,  # Convert to billions
                    'profit_margin': (income_data.get(year, 0) / revenue_data.get(year, 1)) * 100 if revenue_data.get(year, 0) > 0 else 0
                })
        
        # Prepare growth analysis
        growth_analysis = []
        for key, data in self.processed_data.items():
            if data['growth_rates']:
                avg_growth = sum([gr['growth_rate'] for gr in data['growth_rates']]) / len(data['growth_rates'])
                growth_analysis.append({
                    'metric': data['metric_name'],
                    'avg_growth_rate': round(avg_growth, 2),
                    'latest_growth': data['growth_rates'][-1]['growth_rate']
                })
        
        dashboard_data = {
            'company_name': self.raw_data.get('entityName', 'Apple Inc.'),
            'last_updated': datetime.now().isoformat(),
            'summary_metrics': summary_metrics,
            'quarterly_metrics': quarterly_metrics,
            'time_series_data': time_series_data,
            'growth_analysis': growth_analysis,
            'raw_metrics': self.processed_data,
            'data_sources': {
                'annual_forms': '10-K (Annual Reports)',
                'quarterly_forms': '10-Q (Quarterly Reports)',
                'note': 'Dashboard shows most recent data available (quarterly or annual)'
            }
        }
        
        return dashboard_data
    
    def save_dashboard_data(self, filename='apple_sec_dashboard_data.json'):
        """Save processed data to JSON file for dashboard consumption"""
        dashboard_data = self.generate_dashboard_data()
        if dashboard_data:
            with open(filename, 'w') as f:
                json.dump(dashboard_data, f, indent=2, default=str)
            print(f"Dashboard data saved to {filename}")
            return True
        return False

def main():
    """Main function to run the SEC data parser"""
    parser = AppleSECDataParser()
    
    print("Fetching Apple SEC data...")
    if parser.fetch_sec_data():
        print("\nProcessing financial metrics...")
        if parser.process_all_metrics():
            print("\nGenerating dashboard data...")
            if parser.save_dashboard_data():
                print("\n✅ SEC data processing complete!")
                
                # Display summary
                dashboard_data = parser.generate_dashboard_data()
                print(f"\n📊 Dashboard Data Summary:")
                print(f"Company: {dashboard_data['company_name']}")
                print(f"Metrics processed: {len(dashboard_data['summary_metrics'])}")
                print(f"Years of data: {len(dashboard_data['time_series_data'])}")
                
                # Show latest values
                print(f"\n💰 Latest Financial Metrics:")
                for key, metric in dashboard_data['summary_metrics'].items():
                    value_billions = metric['latest_value'] / 1000000000
                    print(f"  {metric['name']}: ${value_billions:.1f}B ({metric['latest_year']}) - Growth: {metric['growth_rate']:.1f}%")
                
                return True
    
    print("❌ Failed to process SEC data")
    return False

if __name__ == "__main__":
    main() 