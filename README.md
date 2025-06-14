# Apple Financial Dashboard - SEC Data Analysis

https://nateyaq.github.io/Apple/demo.html

A comprehensive financial dashboard that displays Apple Inc.'s real financial data sourced directly from SEC EDGAR filings. This project demonstrates advanced data processing, financial analysis, and dashboard visualization capabilities suitable for business systems analyst roles.

## 🚀 Project Overview

This project creates two complementary dashboards:
1. **Sales Analytics Dashboard** (`apple_sales_dashboard.tsx`) - Simulated sales and territory data for business analysis scenarios
2. **Financial Dashboard** (`apple_financial_dashboard.tsx`) - Real SEC filing data from Apple Inc.

### Key Features

- **Real SEC Data Integration**: Fetches actual financial data from SEC EDGAR API
- **Advanced Financial Metrics**: Revenue, Net Income, Assets, Cash Flow, R&D spending
- **Growth Analysis**: Year-over-year growth calculations and trend analysis  
- **Financial Ratios**: Profit margins, ROA, cash ratios, and other key indicators
- **Interactive Visualizations**: Charts and graphs for data exploration
- **Data Quality Validation**: Built-in checks for data accuracy and completeness
- **Professional UI**: Modern, responsive design with Tailwind CSS

## 📁 Project Structure

```
AppleBSA/
├── apple_sec_data_parser.py          # SEC data fetching and processing
├── apple_sec_dashboard_data.json     # Processed SEC data (generated)
├── apple_financial_dashboard.tsx     # React dashboard component
├── apple_sales_dashboard.tsx         # Sales analytics dashboard
├── demo.html                         # HTML demo of financial dashboard
├── Parse-SEC-JSON.py                 # Original SEC parsing script
├── complete_sql_study_chat.md        # SQL study guide for interviews
└── README.md                         # This file
```

## 🛠️ Technical Stack

- **Data Processing**: Python, Pandas, Requests
- **Frontend**: React, TypeScript, Tailwind CSS
- **Charts**: Recharts library
- **Icons**: Lucide React
- **Data Source**: SEC EDGAR API
- **Version Control**: Git

## 📊 Financial Metrics Tracked

### Core Financial Data
- **Total Revenue**: Revenue from SEC 10-K (annual) and 10-Q (quarterly) filings
- **Net Income**: Profit after all expenses and taxes
- **Total Assets**: Complete asset valuation
- **Cash & Cash Equivalents**: Liquid assets available
- **Research & Development**: Innovation investment spending
- **Operating Income**: Core business profitability
- **Shareholders' Equity**: Ownership value

### Calculated Ratios
- **Net Profit Margin**: (Net Income / Revenue) × 100
- **Return on Assets (ROA)**: (Net Income / Total Assets) × 100
- **Cash Ratio**: (Cash & Equivalents / Total Assets) × 100

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+ (for React development)
- Internet connection (for SEC API access)

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AppleBSA
   ```

2. **Install Python dependencies**
   ```bash
   pip install requests pandas numpy matplotlib
   ```

3. **Fetch SEC data**
   ```bash
   python apple_sec_data_parser.py
   ```
   This will generate `apple_sec_dashboard_data.json` with the latest Apple financial data.

4. **View the dashboard**
   - Open `demo.html` in a web browser for the HTML version
   - Or integrate `apple_financial_dashboard.tsx` into a React application

### Running the SEC Data Parser

The SEC data parser automatically:
- Fetches Apple's latest 10-K filings from SEC EDGAR API
- Processes key financial metrics
- Calculates growth rates and trends
- Validates data quality
- Exports structured JSON for dashboard consumption

```bash
python apple_sec_data_parser.py
```

**Sample Output:**
```
Fetching Apple SEC data...
Successfully fetched SEC data for Apple Inc.

Processing financial metrics...
✓ Processed Total Revenue
✓ Processed Net Income
✓ Processed Total Assets
✓ Processed Cash and Cash Equivalents
✓ Processed Research & Development
✓ Processed Operating Income
✓ Processed Shareholders Equity

📊 Dashboard Data Summary:
Company: Apple Inc.
Metrics processed: 7
Years of data: 5

💰 Latest Financial Metrics:
  Total Revenue: $394.3B (2024) - Growth: 2.8%
  Net Income: $93.7B (2024) - Growth: -3.4%
  Total Assets: $365.0B (2024) - Growth: 3.5%
  Cash & Equivalents: $29.9B (2024) - Growth: -0.1%
```

## 📈 Dashboard Features

### Overview Mode
- **Summary Cards**: Key financial metrics with growth indicators
- **Period Selector**: Switch between latest, quarterly, and annual data views
- **Trend Charts**: Revenue and income trends over time
- **Growth Analysis**: Comparative growth rates across metrics
- **Financial Ratios**: Calculated profitability and efficiency ratios

### Detailed Mode
- **Metric Deep Dive**: Detailed timeline for selected metrics
- **Quarterly vs Annual**: Compare quarterly performance to annual figures
- **Quarter-over-Quarter**: Q2 2025 data from latest 10-Q filings
- **Historical Analysis**: Multi-year trend analysis with quarterly granularity

### Data Quality Features
- **Source Validation**: Confirms data from official SEC filings
- **Completeness Checks**: Identifies missing or incomplete data
- **Accuracy Verification**: Cross-validates financial calculations
- **Freshness Indicators**: Shows when data was last updated

## 🎯 Business Applications

This dashboard is designed for:

### Financial Analysis
- **Executive Reporting**: C-level financial performance summaries
- **Investor Relations**: Transparent financial data presentation
- **Strategic Planning**: Historical trend analysis for forecasting
- **Compliance**: SEC-compliant financial data presentation

### Business Intelligence
- **Performance Monitoring**: Track key financial KPIs
- **Competitive Analysis**: Benchmark against industry standards
- **Risk Assessment**: Monitor financial health indicators
- **Decision Support**: Data-driven strategic decisions

## 🔧 Customization

### Adding New Metrics
To add additional financial metrics, modify `apple_sec_data_parser.py`:

```python
metrics_config = {
    'new_metric': {
        'path': 'facts.us-gaap.NewMetricName',
        'name': 'Display Name',
        'fallback_paths': ['alternative.path.if.needed']
    }
}
```

### Styling Customization
The dashboard uses Tailwind CSS classes. Modify colors, spacing, and layout by updating the className attributes in the React components.

### Chart Customization
Charts are built with Recharts. Customize by modifying the chart components in the dashboard files.

## 📋 Data Sources & Compliance

### SEC EDGAR API
- **Official Source**: All data sourced from SEC's official EDGAR database
- **Real-time Access**: Direct API integration for current data
- **GAAP Compliance**: All metrics follow US-GAAP accounting standards
- **CIK Identifier**: Apple Inc. (CIK: 0000320193)
- **10-K Forms**: Annual reports with complete yearly financial data
- **10-Q Forms**: Quarterly reports with most recent quarter data (Q2 2025)

### Data Quality Standards
- **Validation**: Automated checks for data completeness and accuracy
- **Documentation**: Clear data lineage and transformation documentation
- **Audit Trail**: Complete record of data processing steps
- **Error Handling**: Graceful handling of missing or invalid data

## 🎓 Educational Value

This project demonstrates key skills for business systems analyst roles:

### Technical Skills
- **API Integration**: SEC EDGAR API consumption
- **Data Processing**: ETL pipelines with Python/Pandas
- **Frontend Development**: React/TypeScript dashboard creation
- **Data Visualization**: Interactive charts and KPI displays

### Business Skills
- **Financial Analysis**: Understanding of key financial metrics
- **Data Storytelling**: Presenting complex data clearly
- **Stakeholder Communication**: Executive-level reporting
- **Process Documentation**: Clear technical documentation

### Interview Preparation
- **SQL Knowledge**: Complemented by comprehensive SQL study guide
- **Corporate Finance**: Real-world financial data analysis
- **Data Quality**: Built-in validation and governance practices
- **Project Management**: End-to-end project delivery

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:
- Additional financial metrics
- Enhanced visualizations
- Performance improvements
- Documentation updates

## 📄 License

This project is for educational and demonstration purposes. SEC data is publicly available. Please ensure compliance with SEC API usage guidelines.

## 🔗 Related Resources

- [SEC EDGAR API Documentation](https://www.sec.gov/edgar/sec-api-documentation)
- [Apple Inc. SEC Filings](https://www.sec.gov/cik-lookup)
- [US-GAAP Financial Reporting Standards](https://www.fasb.org/gaap)
- [Complete SQL Study Guide](./complete_sql_study_chat.md)

---

**Built for Apple Business Systems Analyst Interview Preparation**  
*Demonstrating real-world financial data analysis and dashboard development capabilities* 
