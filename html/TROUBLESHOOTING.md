# Troubleshooting Guide - Apple Financial Dashboard

## Common Issues and Solutions

### 1. "Error loading financial data" in Browser

**Problem**: The HTML demo shows "Error loading financial data" message.

**Cause**: Modern browsers block local file access for security reasons when opening HTML files directly.

**Solutions**:

#### Option A: Use Local HTTP Server (Recommended)
```bash
# In the project directory
python -m http.server 8000

# Then open in browser:
# http://localhost:8000/demo.html
```

#### Option B: Use Standalone Version
```bash
# Open the standalone version that has embedded data
open demo_standalone.html
```

#### Option C: Disable Browser Security (Not Recommended)
For Chrome, start with: `--allow-file-access-from-files`

### 2. "ModuleNotFoundError: No module named 'requests'"

**Problem**: Python script fails with missing module error.

**Solution**:
```bash
pip install requests pandas numpy matplotlib
```

If using conda:
```bash
conda install requests pandas numpy matplotlib
```

### 3. SEC Data Not Loading/Updating

**Problem**: Dashboard shows old data or fails to fetch new data.

**Solutions**:

#### Refresh SEC Data
```bash
python refresh_data.py
```

#### Manual Data Refresh
```bash
python apple_sec_data_parser.py
```

#### Check Internet Connection
The SEC EDGAR API requires internet access. Verify connection and try again.

### 4. React Dashboard Not Working

**Problem**: TypeScript/React errors in `apple_financial_dashboard.tsx`.

**Solutions**:

#### Install Dependencies
```bash
npm install react recharts lucide-react
npm install -D @types/react typescript
```

#### Use HTML Version Instead
The HTML demo (`demo.html`) provides the same functionality without React setup.

### 5. Charts Not Displaying

**Problem**: Charts show empty or broken.

**Causes & Solutions**:

- **Missing Recharts**: Ensure CDN is loaded or library is installed
- **Data Format Issues**: Check that JSON data is valid
- **Browser Compatibility**: Use modern browser (Chrome, Firefox, Safari, Edge)

### 6. Data Appears Incorrect

**Problem**: Financial metrics seem wrong or outdated.

**Verification Steps**:

1. **Check Data Source**: Verify data comes from SEC EDGAR API
2. **Refresh Data**: Run `python refresh_data.py`
3. **Compare with SEC Filings**: Cross-reference with official Apple 10-K filings
4. **Check Date Range**: Ensure you're looking at the correct fiscal year

### 7. Performance Issues

**Problem**: Dashboard loads slowly or freezes.

**Solutions**:

- **Use Local Server**: Serve files via HTTP server instead of file:// protocol
- **Clear Browser Cache**: Refresh browser cache and reload
- **Check Data Size**: Large datasets may need optimization
- **Update Browser**: Use latest browser version

### 8. Styling Issues

**Problem**: Dashboard looks broken or unstyled.

**Solutions**:

- **Check Tailwind CSS**: Ensure CDN is loading properly
- **Verify Internet**: Tailwind CSS loads from CDN
- **Browser Compatibility**: Use modern browser with CSS Grid support

## Getting Help

### Debug Information to Collect

When reporting issues, please include:

1. **Operating System**: macOS, Windows, Linux
2. **Browser**: Chrome, Firefox, Safari, Edge (with version)
3. **Python Version**: `python --version`
4. **Error Messages**: Full error text from console
5. **Steps to Reproduce**: What you did before the error occurred

### Console Debugging

Open browser developer tools (F12) and check:

1. **Console Tab**: Look for JavaScript errors
2. **Network Tab**: Check if files are loading properly
3. **Application Tab**: Verify local storage and data

### File Verification

Check that these files exist and are not empty:

```bash
ls -la apple_sec_dashboard_data.json
ls -la demo.html
ls -la apple_sec_data_parser.py
```

### Test SEC API Access

Verify SEC API is accessible:

```bash
curl "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json" \
  -H "User-Agent: test@example.com"
```

## Quick Fixes

### Reset Everything
```bash
# Delete generated data and regenerate
rm apple_sec_dashboard_data.json
python apple_sec_data_parser.py
```

### Minimal Test
```bash
# Test with minimal Python script
python -c "import requests; print('Requests working')"
python -c "import pandas; print('Pandas working')"
```

### Browser Test
```bash
# Start simple server and test
python -m http.server 8000 &
open http://localhost:8000/demo.html
```

## Still Having Issues?

1. **Check README.md**: Review setup instructions
2. **Verify Dependencies**: Ensure all required packages are installed
3. **Test Individual Components**: Run each script separately
4. **Use Standalone Version**: Try `demo_standalone.html` for simplest setup

---

**Note**: This dashboard uses real SEC data and requires internet access for data fetching. All financial data is sourced from official SEC EDGAR filings. 