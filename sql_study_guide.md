# SQL Study Guide for Business Systems Analyst

## Core SQL Concepts

### 1. Basic Query Structure
```sql
SELECT column1, column2
FROM table_name
WHERE condition
GROUP BY column1
HAVING group_condition
ORDER BY column1 DESC
LIMIT 10;
```

### 2. Essential SQL Functions

#### Aggregate Functions
- `COUNT()` - Count rows
- `SUM()` - Sum numeric values
- `AVG()` - Calculate average
- `MIN()/MAX()` - Find minimum/maximum values
- `GROUP_CONCAT()` or `STRING_AGG()` - Concatenate values

#### Date/Time Functions
- `DATE()` - Extract date part
- `YEAR()`, `MONTH()`, `DAY()` - Extract date components
- `DATEDIFF()` - Calculate date differences
- `DATE_ADD()` - Add time intervals

#### String Functions
- `CONCAT()` - Combine strings
- `SUBSTRING()` - Extract part of string
- `UPPER()`, `LOWER()` - Change case
- `LENGTH()` - Get string length

### 3. Join Types (Critical for Business Analysis)

#### INNER JOIN
```sql
SELECT a.column1, b.column2
FROM table_a a
INNER JOIN table_b b ON a.id = b.a_id;
```

#### LEFT JOIN
```sql
SELECT a.column1, b.column2
FROM table_a a
LEFT JOIN table_b b ON a.id = b.a_id;
```

#### FULL OUTER JOIN
```sql
SELECT a.column1, b.column2
FROM table_a a
FULL OUTER JOIN table_b b ON a.id = b.a_id;
```

### 4. Window Functions (Advanced but Important)

#### ROW_NUMBER()
```sql
SELECT 
    product_name,
    sales_amount,
    ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales_amount DESC) as rank
FROM sales_data;
```

#### RANK() and DENSE_RANK()
```sql
SELECT 
    employee_name,
    salary,
    RANK() OVER (ORDER BY salary DESC) as salary_rank
FROM employees;
```

#### LAG() and LEAD()
```sql
SELECT 
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) as previous_month_revenue
FROM monthly_revenue;
```

### 5. Subqueries and CTEs

#### Subquery Example
```sql
SELECT product_name, price
FROM products
WHERE price > (SELECT AVG(price) FROM products);
```

#### Common Table Expression (CTE)
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

### 6. Data Quality and Validation

#### Finding Duplicates
```sql
SELECT column1, column2, COUNT(*)
FROM table_name
GROUP BY column1, column2
HAVING COUNT(*) > 1;
```

#### Handling NULL Values
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

## Business Analyst Specific SQL Patterns

### 1. Time-Based Analysis
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

### 2. Cohort Analysis
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

### 3. Performance Metrics
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

## Common Interview Question Types

### 1. Data Aggregation and Reporting
- "Find the top 10 selling products by revenue"
- "Calculate monthly active users"
- "Determine customer lifetime value"

### 2. Data Quality Issues
- "Identify duplicate records"
- "Find missing or inconsistent data"
- "Validate data integrity across tables"

### 3. Business Logic Implementation
- "Calculate employee bonuses based on performance tiers"
- "Determine product categories with declining sales"
- "Find customers who haven't made purchases in the last 6 months"

### 4. Performance and Optimization
- "Optimize a slow-running query"
- "Design indexes for better performance"
- "Rewrite correlated subqueries as joins"

## Apple-Specific SQL Requirements (Based on Job Posting)

### 1. Advanced SQL for Data Engineering Integration
- **Interpret Data Engineering work**: Understand complex upstream data flows
- **Data pipeline integration**: Work with ETL/ELT processes from Snowflake to AWS S3
- **Cross-system data relationships**: Map data lineage across multiple sources

### 2. Corporate Finance Context
- **Revenue recognition queries**: Understanding deferred revenue, bookings vs billings
- **Sales performance metrics**: Territory analysis, quota attainment, forecasting
- **Retail analytics**: Store performance, inventory turnover, seasonal trends

### 3. Data Quality and Governance
- **Built-in data validation**: SQL checks for accuracy before dashboard distribution
- **Documentation of data nuances**: Understanding business process impacts on data
- **Upstream source mapping**: Trace data from source systems through transformations

### Key Tips for Apple SQL Interview

### 1. Think Corporate Finance First
- Frame SQL solutions in terms of strategic finance decisions
- Consider how reports will inform executive-level choices
- Understand sales/retail business processes impact on data

### 2. Demonstrate Data Pipeline Knowledge
- Show understanding of ETL/ELT concepts
- Discuss data quality checks within SQL
- Reference experience with cloud data warehouses (Snowflake, AWS)

### 3. Advanced SQL Proficiency
- Complex joins across multiple data sources
- Window functions for time-series analysis
- Performance optimization for large datasets

### 4. Business Communication
- Explain technical concepts to non-technical stakeholders
- Translate business requirements into technical specifications
- Discuss delivery timelines and dependencies

## Sample Practice Problems

### Easy Level
1. Find all customers who made purchases in the last 30 days
2. Calculate total revenue by product category
3. List employees with salaries above the company average

### Medium Level
1. Find the second highest salary in each department
2. Calculate month-over-month growth rates
3. Identify customers with no purchases in the last quarter

### Advanced Level
1. Create a customer segmentation based on purchase behavior
2. Calculate running totals and moving averages
3. Perform cohort analysis for user retention

## Database Design Concepts

### Normalization
- Understand 1NF, 2NF, 3NF
- When and why to denormalize for analytics

### Indexes
- Primary keys and foreign keys
- Composite indexes for multi-column queries
- Impact on query performance

### Data Types
- Choose appropriate data types for efficiency
- Understand implications of VARCHAR vs CHAR
- Date/time data type considerations

Remember: As a Business Systems Analyst, your SQL skills should focus on extracting insights, ensuring data quality, and supporting business decision-making rather than just technical query writing.
