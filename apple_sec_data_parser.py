import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
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
    
    def extract_financial_metric(self, metric_path, metric_name):
        """Extract a specific financial metric from the SEC data"""
        try:
            # Navigate through the nested structure
            current_data = self.raw_data
            for key in metric_path.split('.'):
                current_data = current_data[key]
            
            # Extract USD values
            if 'units' in current_data and 'USD' in current_data['units']:
                df = pd.DataFrame(current_data['units']['USD'])
                
                # Filter for annual data (10-K forms) and recent years
                annual_data = df[df['form'] == '10-K'].copy()
                if len(annual_data) > 0:
                    annual_data['end'] = pd.to_datetime(annual_data['end'])
                    annual_data = annual_data.sort_values('end')
                    
                    # Get last 5 years of data
                    recent_data = annual_data.tail(5)
                    
                    return {
                        'metric_name': metric_name,
                        'data': recent_data[['end', 'val', 'fy']].to_dict('records'),
                        'latest_value': recent_data['val'].iloc[-1] if len(recent_data) > 0 else 0,
                        'latest_year': recent_data['fy'].iloc[-1] if len(recent_data) > 0 else None
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
    
    def process_all_metrics(self):
        """Process all key financial metrics for the dashboard"""
        if not self.raw_data:
            print("No SEC data available. Please fetch data first.")
            return False
        
        # Define key financial metrics to extract
        metrics_config = {
            'revenue': {
                'path': 'facts.us-gaap.RevenueFromContractWithCustomerExcludingAssessedTax',
                'name': 'Total Revenue',
                'fallback_paths': [
                    'facts.us-gaap.Revenues',
                    'facts.us-gaap.SalesRevenueNet',
                    'facts.us-gaap.RevenueFromContractWithCustomerIncludingAssessedTax',
                    'facts.us-gaap.SalesRevenueGoodsNet',
                    'facts.us-gaap.RevenueFromSaleOfGoods'
                ]
            },
            'net_income': {
                'path': 'facts.us-gaap.NetIncomeLoss',
                'name': 'Net Income'
            },
            'total_assets': {
                'path': 'facts.us-gaap.Assets',
                'name': 'Total Assets'
            },
            'cash_and_equivalents': {
                'path': 'facts.us-gaap.CashAndCashEquivalentsAtCarryingValue',
                'name': 'Cash and Cash Equivalents'
            },
            'research_development': {
                'path': 'facts.us-gaap.ResearchAndDevelopmentExpense',
                'name': 'Research & Development'
            },
            'operating_income': {
                'path': 'facts.us-gaap.OperatingIncomeLoss',
                'name': 'Operating Income'
            },
            'shareholders_equity': {
                'path': 'facts.us-gaap.StockholdersEquity',
                'name': 'Shareholders Equity'
            }
        }
        
        # Extract each metric
        for key, config in metrics_config.items():
            metric_data = self.extract_financial_metric(config['path'], config['name'])
            
            # Try fallback paths if primary path fails
            if not metric_data and 'fallback_paths' in config:
                for fallback_path in config['fallback_paths']:
                    metric_data = self.extract_financial_metric(fallback_path, config['name'])
                    if metric_data:
                        break
            
            if metric_data:
                # Calculate growth rates
                growth_rates = self.calculate_growth_rates(metric_data['data'])
                metric_data['growth_rates'] = growth_rates
                
                self.processed_data[key] = metric_data
                print(f"✓ Processed {config['name']}")
            else:
                print(f"✗ Could not process {config['name']}")
        
        return True
    
    def generate_dashboard_data(self):
        """Generate structured data for the dashboard"""
        if not self.processed_data:
            print("No processed data available. Please process metrics first.")
            return None
        
        # Prepare summary metrics
        summary_metrics = {}
        for key, data in self.processed_data.items():
            summary_metrics[key] = {
                'name': data['metric_name'],
                'latest_value': data['latest_value'],
                'latest_year': data['latest_year'],
                'growth_rate': data['growth_rates'][-1]['growth_rate'] if data['growth_rates'] else 0
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
            'time_series_data': time_series_data,
            'growth_analysis': growth_analysis,
            'raw_metrics': self.processed_data
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