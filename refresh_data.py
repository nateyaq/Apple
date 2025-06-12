#!/usr/bin/env python3
"""
Quick script to refresh Apple SEC data for the dashboard.
Run this script to update the dashboard with the latest financial data.
"""

import sys
import os
from apple_sec_data_parser import AppleSECDataParser

def main():
    print("🍎 Apple Financial Dashboard - Data Refresh")
    print("=" * 50)
    
    # Initialize parser
    parser = AppleSECDataParser()
    
    try:
        print("📡 Fetching latest SEC data from EDGAR API...")
        if not parser.fetch_sec_data():
            print("❌ Failed to fetch SEC data")
            return False
        
        print("⚙️  Processing financial metrics...")
        if not parser.process_all_metrics():
            print("❌ Failed to process metrics")
            return False
        
        print("💾 Saving dashboard data...")
        if not parser.save_dashboard_data():
            print("❌ Failed to save data")
            return False
        
        # Display summary
        dashboard_data = parser.generate_dashboard_data()
        print("\n✅ Data refresh completed successfully!")
        print(f"📊 Company: {dashboard_data['company_name']}")
        print(f"📈 Metrics processed: {len(dashboard_data['summary_metrics'])}")
        print(f"📅 Last updated: {dashboard_data['last_updated']}")
        
        print("\n💰 Latest Financial Snapshot:")
        for key, metric in dashboard_data['summary_metrics'].items():
            value_billions = metric['latest_value'] / 1000000000
            print(f"  • {metric['name']}: ${value_billions:.1f}B ({metric['latest_year']}) [{metric['growth_rate']:+.1f}%]")
        
        print(f"\n🎯 Dashboard ready! Open demo.html to view the updated data.")
        return True
        
    except Exception as e:
        print(f"❌ Error during data refresh: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 