# Complete SQL Study Guide Business Systems Analyst

## Table of Contents
1. [Core SQL Study Guide](#core-sql-study-guide)
2. [Denormalization for Analytics Deep Dive](#denormalization-for-analytics-deep-dive)
3. [Job Posting Analysis](#apple-job-posting-analysis)
4. [Job-Specific Interview Scenario](#apple-specific-interview-scenario)

---

## Core SQL Study Guide

### Essential SQL Concepts You Must Know

#### 1. Basic Query Structure
```sql
SELECT column1, column2
FROM table_name
WHERE condition
GROUP BY column1
HAVING group_condition
ORDER BY column1 DESC
LIMIT 10;
```

#### 2. Essential SQL Functions

##### Aggregate Functions
- `COUNT()` - Count rows
- `SUM()` - Sum numeric values
- `AVG()` - Calculate average
- `MIN()/MAX()` - Find minimum/maximum values
- `GROUP_CONCAT()` or `STRING_AGG()` - Concatenate values

##### Date/Time Functions
- `DATE()` - Extract date part
- `YEAR()`, `MONTH()`, `DAY()` - Extract date components
- `DATEDIFF()` - Calculate date differences
- `DATE_ADD()` - Add time intervals

##### String Functions
- `CONCAT()` - Combine strings
- `SUBSTRING()` - Extract part of string
- `UPPER()`, `LOWER()` - Change case
- `LENGTH()` - Get string length

#### 3. Join Types (Critical for Business Analysis)

##### INNER JOIN
```sql
SELECT a.column1, b.column2
FROM table_a a
INNER JOIN table_b b ON a.id = b.a_id;
```

##### LEFT JOIN
```sql
SELECT a.column1, b.column2
FROM table_a a
LEFT JOIN table_b b ON a.id = b.a_id;
```

##### FULL OUTER JOIN
```sql
SELECT a.column1, b.column2
FROM table_a a
FULL OUTER JOIN table_b b ON a.id = b.a_id;
```

#### 4. Window Functions (Advanced but Important)

##### ROW_NUMBER()
```sql
SELECT 
    product_name,
    sales_amount,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales_amount DESC) as rank
FROM sales_data;
```

##### RANK() and DENSE_RANK()
```sql
SELECT 
    employee_name,
    salary,
    RANK() OVER (ORDER BY salary DESC) as salary_rank
FROM employees;
```

##### LAG() and LEAD()
```sql
SELECT 
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) as previous_month_revenue
FROM monthly_revenue;
```

#### 5. Subqueries and CTEs

##### Subquery Example
```sql
SELECT product_name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products);
```

##### Common Table Expression (CTE)
```sql
WITH high_value_customers AS (
    SELECT customer_id, SUM(order_amount) as total_spent
    FROM orders
    GROUP BY customer_id
    HAVING SUM(order_amount) > 1000
)
SELECT c.customer_name, hvc.total_spent
FROM customers c
JOIN high_value_customers hvc ON c.customer_id = hvc.customer_id;
```

#### 6. Data Quality and Validation

##### Finding Duplicates
```sql
SELECT column1, column2, COUNT(*)
FROM table_name
GROUP BY column1, column2
HAVING COUNT(*) > 1;
```

##### Handling NULL Values
```sql
SELECT 
    column1,
    COALESCE(column2, 'Default Value') as column2_clean,
    CASE 
        WHEN column3 IS NULL THEN 'Missing'
        ELSE column3
    END as column3_clean
FROM table_name;
```

### Business Analyst Specific SQL Patterns

#### 1. Time-Based Analysis
```sql
-- Year-over-year growth
SELECT 
    YEAR(order_date) as year,
    SUM(order_amount) as total_revenue,
    LAG(SUM(order_amount)) OVER (ORDER BY YEAR(order_date)) as prev_year_revenue,
    ((SUM(order_amount) - LAG(SUM(order_amount)) OVER (ORDER BY YEAR(order_date))) / 
     LAG(SUM(order_amount)) OVER (ORDER BY YEAR(order_date))) * 100 as yoy_growth_percent
FROM orders
GROUP BY YEAR(order_date);
```

#### 2. Cohort Analysis
```sql
-- Customer retention by signup month
WITH customer_cohorts AS (
    SELECT 
        customer_id,
        DATE_TRUNC('month', signup_date) as cohort_month
    FROM customers
),
customer_activities AS (
    SELECT 
        c.customer_id,
        c.cohort_month,
        DATE_TRUNC('month', o.order_date) as activity_month
    FROM customer_cohorts c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
)
SELECT 
    cohort_month,
    activity_month,
    COUNT(DISTINCT customer_id) as active_customers
FROM customer_activities
WHERE activity_month IS NOT NULL
GROUP BY cohort_month, activity_month
ORDER BY cohort_month, activity_month;
```

#### 3. Performance Metrics
```sql
-- Calculate conversion rates
SELECT 
    marketing_channel,
    COUNT(*) as total_visitors,
    SUM(CASE WHEN purchased = 1 THEN 1 ELSE 0 END) as conversions,
    (SUM(CASE WHEN purchased = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as conversion_rate
FROM website_visits
GROUP BY marketing_channel
ORDER BY conversion_rate DESC;
```

### Job-Specific SQL Requirements

#### 1. Advanced SQL for Data Engineering Integration
- **Interpret Data Engineering work**: Understand complex upstream data flows
- **Data pipeline integration**: Work with ETL/ELT processes from Snowflake to AWS S3
- **Cross-system data relationships**: Map data lineage across multiple sources

#### 2. Corporate Finance Context
- **Revenue recognition queries**: Understanding deferred revenue, bookings vs billings
- **Sales performance metrics**: Territory analysis, quota attainment, forecasting
- **Retail analytics**: Store performance, inventory turnover, seasonal trends

#### 3. Data Quality and Governance
- **Built-in data validation**: SQL checks for accuracy before dashboard distribution
- **Documentation of data nuances**: Understanding business process impacts on data
- **Upstream source mapping**: Trace data from source systems through transformations

### Key Tips for SQL Interview

#### 1. Think Corporate Finance First
- Frame SQL solutions in terms of strategic finance decisions
- Consider how reports will inform executive-level choices
- Understand sales/retail business processes impact on data

#### 2. Demonstrate Data Pipeline Knowledge
- Show understanding of ETL/ELT concepts
- Discuss data quality checks within SQL
- Reference experience with cloud data warehouses (Snowflake, AWS)

#### 3. Advanced SQL Proficiency
- Complex joins across multiple data sources
- Window functions for time-series analysis
- Performance optimization for large datasets

#### 4. Business Communication
- Explain technical concepts to non-technical stakeholders
- Translate business requirements into technical specifications
- Discuss delivery timelines and dependencies

### Common Interview Question Types

#### 1. Data Aggregation and Reporting
- "Find the top 10 selling products by revenue"
- "Calculate monthly active users"
- "Determine customer lifetime value"

#### 2. Data Quality Issues
- "Identify duplicate records"
- "Find missing or inconsistent data"
- "Validate data integrity across tables"

#### 3. Business Logic Implementation
- "Calculate employee bonuses based on performance tiers"
- "Determine product categories with declining sales"
- "Find customers who haven't made purchases in the last 6 months"

#### 4. Performance and Optimization
- "Optimize a slow-running query"
- "Design indexes for better performance"
- "Rewrite correlated subqueries as joins"

### Sample Practice Problems

#### Easy Level
1. Find all customers who made purchases in the last 30 days
2. Calculate total revenue by product category
3. List employees with salaries above the company average

#### Medium Level
1. Find the second highest salary in each department
2. Calculate month-over-month growth rates
3. Identify customers with no purchases in the last quarter

#### Advanced Level
1. Create a customer segmentation based on purchase behavior
2. Calculate running totals and moving averages
3. Perform cohort analysis for user retention

### Database Design Concepts

#### Normalization
- Understand 1NF, 2NF, 3NF
- When and why to denormalize for analytics

#### Indexes
- Primary keys and foreign keys
- Composite indexes for multi-column queries
- Impact on query performance

#### Data Types
- Choose appropriate data types for efficiency
- Understand implications of VARCHAR vs CHAR
- Date/time data type considerations

---

## Denormalization for Analytics Deep Dive

### What is Denormalization?

**Normalization** creates a "clean" database structure where data isn't duplicated and follows rules (1NF, 2NF, 3NF) to eliminate redundancy.

**Denormalization** deliberately breaks these rules by introducing redundancy to improve query performance and simplify analysis.

### Normalized vs Denormalized: A Real Example

#### Normalized Structure (Good for OLTP - Transactional Systems)
```sql
-- Customers table
customers (customer_id, customer_name, email, signup_date)

-- Orders table  
orders (order_id, customer_id, order_date, total_amount)

-- Order_items table
order_items (item_id, order_id, product_id, quantity, unit_price)

-- Products table
products (product_id, product_name, category_id, current_price)

-- Categories table
categories (category_id, category_name)
```

#### Denormalized Structure (Good for Analytics)
```sql
-- Single analytics table
order_analytics (
    order_id,
    customer_id,
    customer_name,           -- Duplicated from customers
    customer_email,          -- Duplicated from customers
    customer_signup_date,    -- Duplicated from customers
    order_date,
    product_id,
    product_name,            -- Duplicated from products
    category_name,           -- Duplicated from categories
    quantity,
    unit_price,
    line_total,
    order_total              -- Duplicated across all line items
)
```

### When to Denormalize for Analytics

#### 1. Frequent Complex Joins Are Killing Performance

**Problem with Normalized Data:**
```sql
-- This query touches 5 tables - slow for large datasets
SELECT 
    c.customer_name,
    cat.category_name,
    SUM(oi.quantity * oi.unit_price) as revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN categories cat ON p.category_id = cat.category_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.customer_name, cat.category_name;
```

**Solution with Denormalized Data:**
```sql
-- Much faster - single table scan
SELECT 
    customer_name,
    category_name,
    SUM(line_total) as revenue
FROM order_analytics
WHERE order_date >= '2024-01-01'
GROUP BY customer_name, category_name;
```

#### 2. Analysts Need Self-Service Access

Business analysts often aren't SQL experts. A denormalized table lets them query data without understanding complex relationships.

#### 3. Historical Data Needs to Be Preserved

In normalized systems, if a product name changes, it changes everywhere. For analytics, you often want to see historical data as it was.

#### 4. Reporting and BI Tools Work Better

Tools like Tableau, Power BI, and Excel work much better with flat, denormalized structures.

### Why Denormalize for Analytics

#### Performance Benefits

**1. Fewer Joins = Faster Queries**
```sql
-- Normalized: 5-table join (slow)
SELECT customer_name, product_name, category_name, SUM(revenue)
FROM [5 table join]

-- Denormalized: Single table (fast)
SELECT customer_name, product_name, category_name, SUM(revenue)
FROM order_analytics
```

**2. Better Index Utilization**
```sql
-- Can create composite indexes on frequently queried combinations
CREATE INDEX idx_analytics_date_category 
ON order_analytics (order_date, category_name);
```

**3. Reduced I/O Operations**
- Single table scan vs multiple table reads
- Data locality - related information stored together

### Common Denormalization Patterns for Analytics

#### 1. Fact Tables with Dimensions Embedded
```sql
-- Instead of separate dimension tables, embed key attributes
sales_fact (
    date_key,
    product_id,
    product_name,        -- Denormalized
    product_category,    -- Denormalized
    customer_id,
    customer_segment,    -- Denormalized
    sales_amount
)
```

#### 2. Pre-Calculated Aggregates
```sql
-- Store commonly needed calculations
monthly_customer_summary (
    customer_id,
    year_month,
    total_orders,        -- Pre-calculated
    total_revenue,       -- Pre-calculated
    avg_order_value,     -- Pre-calculated
    days_since_last_order -- Pre-calculated
)
```

#### 3. Flattened Hierarchies
```sql
-- Instead of product -> subcategory -> category hierarchy
product_analytics (
    product_id,
    product_name,
    subcategory_name,    -- Flattened
    category_name,       -- Flattened
    department_name      -- Flattened
)
```

### Trade-offs and Considerations

#### Advantages
- **Faster query performance** for analytics
- **Simpler queries** for business users
- **Better tool compatibility**
- **Historical data preservation**

#### Disadvantages
- **Storage overhead** (data duplication)
- **Data synchronization complexity**
- **Update anomalies** (same data in multiple places)
- **Increased ETL complexity**

---

## Apple Job Posting Analysis

### Key Requirements Summary

**Position**: Business Systems Analyst - Sales & Finance Analytics
**Location**: Cupertino, California

### Core Responsibilities
- Work cross-functionally with sales, finance and technical teams
- Develop new tools, processes and analysis for senior sales/finance executives
- Analyze large datasets to inform key stakeholders of business opportunities
- Build data pipelines using ELT and ETL (Snowflake to AWS S3)
- Create data visualizations, dashboards, and reports using SQL, Python and Tableau
- Transform transactional data into analytical datasets
- Manage long-term roadmap for analytics tools and systems

### Minimum Qualifications
- Master's degree in Finance, IT & Analytics, or related field
- 2 years of experience in each of the following:
  - Contextualizing business requests in Corporate Finance context
  - Python for data orchestration and quality checking
  - Data visualization tools for executive dashboards
  - Business process documentation and Data Governance
  - Agile Project Management (Jira)
  - Advanced SQL interpretation of Data Engineering work

### Key Skills Emphasis
1. **Corporate Finance Context** - Understanding strategic finance decisions
2. **Advanced SQL** - Interpreting complex upstream data flows
3. **Data Quality Focus** - Building quality checks into pipelines
4. **Cross-functional Communication** - Working with technical and business teams
5. **Project Management** - Agile methodology and stakeholder management

---

## Apple-Specific Interview Scenario

### Scenario: Sales & Finance Analytics for Quarterly Business Review

**Context**: You're supporting Apple's Worldwide Sales and Finance teams for a quarterly business review with senior finance leadership. Data comes from CRM (Salesforce), ERP systems, and retail POS systems, consolidated in Snowflake data warehouse.

### Realistic Apple Database Schema

```sql
-- Sales transactions from all channels
sales_transactions (
    transaction_id, product_sku, channel, territory, 
    transaction_date, quantity, unit_price, total_amount,
    sales_rep_id, customer_id
)

-- Product hierarchy 
products (
    product_sku, product_name, product_line, category,
    cost_of_goods, launch_date, discontinue_date
)

-- Sales territories and quotas
territories (
    territory_id, territory_name, region, sales_rep_id,
    quarterly_quota, manager_id
)

-- Channel definitions
sales_channels (
    channel_id, channel_name, channel_type, 
    commission_rate, fulfillment_cost_pct
)

-- Customer segments
customers (
    customer_id, customer_name, segment, 
    first_purchase_date, total_lifetime_value
)
```

### Business Question
"Finance wants to understand which product lines and territories are tracking toward their Q2 quotas, with particular concern about profitability by channel. They also want trends compared to Q1."

### Step-by-Step Solution

#### Step 1: Clarifying Questions You Should Ask
1. "Should profitability include fulfillment costs and commissions?"
2. "Do you want quota tracking by territory or individual sales rep?"
3. "Should I use booking date or revenue recognition date?"
4. "Are there specific product lines of highest concern to finance?"

#### Step 2: Core Performance Analysis

```sql
-- Current quarter performance with profitability
WITH q2_performance AS (
    SELECT 
        t.territory_name,
        t.region,
        p.product_line,
        sc.channel_name,
        sc.channel_type,
        
        -- Sales metrics
        COUNT(st.transaction_id) as transaction_count,
        SUM(st.quantity) as units_sold,
        SUM(st.total_amount) as gross_revenue,
        
        -- Profitability calculations
        SUM(st.quantity * p.cost_of_goods) as total_cogs,
        SUM(st.total_amount * sc.commission_rate) as commission_costs,
        SUM(st.total_amount * sc.fulfillment_cost_pct) as fulfillment_costs,
        
        -- Net revenue calculation
        SUM(st.total_amount) - 
        SUM(st.quantity * p.cost_of_goods) - 
        SUM(st.total_amount * sc.commission_rate) - 
        SUM(st.total_amount * sc.fulfillment_cost_pct) as net_revenue,
        
        -- Territory quota information
        MAX(t.quarterly_quota) as territory_quota
        
    FROM sales_transactions st
    JOIN products p ON st.product_sku = p.product_sku
    JOIN territories t ON st.territory = t.territory_id
    JOIN sales_channels sc ON st.channel = sc.channel_id
    WHERE st.transaction_date >= '2024-04-01' 
        AND st.transaction_date < '2024-07-01'
        AND p.discontinue_date IS NULL  -- Only active products
    GROUP BY t.territory_name, t.region, p.product_line, 
             sc.channel_name, sc.channel_type, t.quarterly_quota
)
SELECT 
    territory_name,
    region,
    product_line,
    channel_name,
    channel_type,
    transaction_count,
    units_sold,
    gross_revenue,
    net_revenue,
    territory_quota,
    
    -- Key finance metrics
    ROUND((net_revenue / gross_revenue) * 100, 2) as net_margin_pct,
    ROUND((gross_revenue / territory_quota) * 100, 2) as quota_attainment_pct,
    
    -- Performance indicators
    CASE 
        WHEN (gross_revenue / territory_quota) >= 0.95 THEN 'On Track'
        WHEN (gross_revenue / territory_quota) >= 0.80 THEN 'At Risk'
        ELSE 'Needs Attention'
    END as quota_status
    
FROM q2_performance
ORDER BY net_revenue DESC;
```

#### Step 3: Quarter-over-Quarter Comparison

```sql
-- Enhanced analysis with Q1 comparison
WITH quarterly_performance AS (
    SELECT 
        t.territory_name,
        t.region,
        p.product_line,
        sc.channel_name,
        
        -- Determine quarter
        CASE 
            WHEN st.transaction_date >= '2024-01-01' AND st.transaction_date < '2024-04-01' THEN 'Q1'
            WHEN st.transaction_date >= '2024-04-01' AND st.transaction_date < '2024-07-01' THEN 'Q2'
        END as quarter,
        
        SUM(st.total_amount) as gross_revenue,
        SUM(st.total_amount) - 
        SUM(st.quantity * p.cost_of_goods) - 
        SUM(st.total_amount * sc.commission_rate) - 
        SUM(st.total_amount * sc.fulfillment_cost_pct) as net_revenue,
        
        COUNT(st.transaction_id) as transaction_count
        
    FROM sales_transactions st
    JOIN products p ON st.product_sku = p.product_sku
    JOIN territories t ON st.territory = t.territory_id
    JOIN sales_channels sc ON st.channel = sc.channel_id
    WHERE st.transaction_date >= '2024-01-01' 
        AND st.transaction_date < '2024-07-01'
        AND p.discontinue_date IS NULL
    GROUP BY t.territory_name, t.region, p.product_line, 
             sc.channel_name, quarter
),
pivot_comparison AS (
    SELECT 
        territory_name,
        region,
        product_line,
        channel_name,
        
        SUM(CASE WHEN quarter = 'Q1' THEN gross_revenue ELSE 0 END) as q1_gross_revenue,
        SUM(CASE WHEN quarter = 'Q2' THEN gross_revenue ELSE 0 END) as q2_gross_revenue,
        SUM(CASE WHEN quarter = 'Q1' THEN net_revenue ELSE 0 END) as q1_net_revenue,
        SUM(CASE WHEN quarter = 'Q2' THEN net_revenue ELSE 0 END) as q2_net_revenue
        
    FROM quarterly_performance
    GROUP BY territory_name, region, product_line, channel_name
)
SELECT 
    territory_name,
    region,
    product_line,
    channel_name,
    q1_gross_revenue,
    q2_gross_revenue,
    q1_net_revenue,
    q2_net_revenue,
    
    -- Growth calculations
    CASE 
        WHEN q1_gross_revenue > 0 
        THEN ROUND(((q2_gross_revenue - q1_gross_revenue) / q1_gross_revenue) * 100, 2)
        ELSE NULL 
    END as revenue_growth_pct,
    
    CASE 
        WHEN q1_net_revenue > 0 
        THEN ROUND(((q2_net_revenue - q1_net_revenue) / q1_net_revenue) * 100, 2)
        ELSE NULL 
    END as profit_growth_pct,
    
    -- Margin comparison
    CASE 
        WHEN q1_gross_revenue > 0 
        THEN ROUND((q1_net_revenue / q1_gross_revenue) * 100, 2)
        ELSE NULL 
    END as q1_margin_pct,
    
    CASE 
        WHEN q2_gross_revenue > 0 
        THEN ROUND((q2_net_revenue / q2_gross_revenue) * 100, 2)
        ELSE NULL 
    END as q2_margin_pct

FROM pivot_comparison
WHERE q1_gross_revenue > 0 OR q2_gross_revenue > 0  -- Only include active combinations
ORDER BY q2_net_revenue DESC;
```

#### Step 4: Data Quality Validation (Critical for Apple)

```sql
-- Data quality validation queries
-- Check 1: Identify potential data issues
SELECT 'Revenue Anomalies' as check_type,
       COUNT(*) as issue_count
FROM sales_transactions 
WHERE total_amount <= 0 OR total_amount > 50000  -- Unusual transaction amounts

UNION ALL

SELECT 'Missing Product Information' as check_type,
       COUNT(*) as issue_count
FROM sales_transactions st
LEFT JOIN products p ON st.product_sku = p.product_sku
WHERE p.product_sku IS NULL

UNION ALL

SELECT 'Future Dated Transactions' as check_type,
       COUNT(*) as issue_count
FROM sales_transactions 
WHERE transaction_date > CURRENT_DATE

UNION ALL

SELECT 'Quota Data Completeness' as check_type,
       COUNT(*) as issue_count
FROM territories 
WHERE quarterly_quota IS NULL OR quarterly_quota <= 0;

-- Check 2: Revenue reconciliation
SELECT 
    'Data Reconciliation' as validation_type,
    SUM(total_amount) as total_recorded_revenue,
    COUNT(DISTINCT territory) as territories_with_data,
    MIN(transaction_date) as earliest_transaction,
    MAX(transaction_date) as latest_transaction
FROM sales_transactions 
WHERE transaction_date >= '2024-04-01' 
    AND transaction_date < '2024-07-01';
```

### Executive Summary Framework

When presenting to finance leadership, structure your findings as:

1. **Performance Summary**: Overall Q2 quota attainment and margin performance
2. **Key Concerns**: Territories or product lines requiring intervention
3. **Channel Performance**: Margin and volume analysis by sales channel
4. **Growth Trends**: Quarter-over-quarter performance insights
5. **Recommendations**: Actionable insights for sales and finance teams

### Key Skills This Scenario Demonstrates

1. **Corporate Finance Context**: Understanding quotas, margins, profitability
2. **Advanced SQL**: Complex joins, window functions, data validation
3. **Data Quality Focus**: Proactive identification of data issues
4. **Business Communication**: Translating technical analysis into executive insights
5. **Cross-functional Thinking**: Considering sales, finance, and operational perspectives

---

## Final Interview Preparation Tips

### Before the Interview
1. **Review Apple's Financial Structure**: Understand their sales channels, product lines, and business model
2. **Practice Complex SQL**: Focus on multi-table joins and window functions
3. **Prepare Business Questions**: Think about what finance executives would want to know
4. **Study Data Quality Patterns**: Be ready to discuss data validation approaches

### During the Interview
1. **Ask Clarifying Questions**: Always understand the business context first
2. **Think Out Loud**: Explain your reasoning as you build queries
3. **Consider Data Quality**: Mention potential issues and validation steps
4. **Frame in Business Terms**: Connect technical solutions to business impact

### Key Success Factors
- Demonstrate understanding of corporate finance concepts
- Show advanced SQL skills with business context
- Emphasize data quality and governance mindset
- Communicate technical concepts clearly to business stakeholders
- Think cross-functionally about sales, finance, and operations

Remember: As a Business Systems Analyst at Apple, your SQL skills should focus on extracting insights, ensuring data quality, and supporting strategic business decision-making rather than just technical query writing.
