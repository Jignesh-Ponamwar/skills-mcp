---
name: sql-query-writer
description: Write optimized SQL queries for complex data requirements. Handle multi-table joins, aggregations, window functions, CTEs, subqueries, and performance optimization. Use when the user needs to write a SQL query, optimize a slow query, understand a query plan, design a schema, or work with database data.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [sql, database, postgresql, mysql, sqlite, queries, optimization]
  platforms: [claude-code, cursor, any]
  triggers:
    - write a SQL query
    - SQL query for
    - query this database
    - optimize this SQL
    - slow query
    - SQL join
    - aggregate data in SQL
    - window function
    - CTE
    - database query
    - write SQL to find
    - SQL performance
---

# SQL Query Writer Skill

## Overview
Write correct, readable, and performant SQL queries. Covers SELECT fundamentals through advanced window functions, CTEs, and performance optimization. Dialect-aware: PostgreSQL, MySQL, SQLite, BigQuery.

## Step-by-Step Process

### Step 1: Understand the Data Model
Before writing a query, confirm:
- **Tables involved** and their primary keys
- **Join relationships** (1:1, 1:many, many:many via junction table)
- **Data types** of filter and join columns
- **Approximate row counts** (affects optimization strategy)
- **Target dialect** (PostgreSQL, MySQL, SQLite, BigQuery, DuckDB)

### Step 2: Start with the Simplest Correct Query

```sql
-- Start simple, then optimize
SELECT
    u.id,
    u.name,
    u.email,
    COUNT(o.id) AS order_count,
    SUM(o.total_amount) AS total_spent
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at >= '2024-01-01'
GROUP BY u.id, u.name, u.email
ORDER BY total_spent DESC
LIMIT 100;
```

### Step 3: Common Query Patterns

**Top N per group (window function)**
```sql
SELECT *
FROM (
    SELECT
        product_id,
        category,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rank
    FROM product_sales
) ranked
WHERE rank <= 5;
```

**Running totals and moving averages**
```sql
SELECT
    date,
    revenue,
    SUM(revenue) OVER (ORDER BY date) AS cumulative_revenue,
    AVG(revenue) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS revenue_7d_avg
FROM daily_sales
ORDER BY date;
```

**Year-over-year comparison**
```sql
SELECT
    DATE_TRUNC('month', order_date) AS month,
    SUM(total) AS revenue,
    LAG(SUM(total), 12) OVER (ORDER BY DATE_TRUNC('month', order_date)) AS revenue_prev_year,
    ROUND(
        (SUM(total) - LAG(SUM(total), 12) OVER (ORDER BY DATE_TRUNC('month', order_date)))
        / NULLIF(LAG(SUM(total), 12) OVER (ORDER BY DATE_TRUNC('month', order_date)), 0) * 100,
        1
    ) AS yoy_pct_change
FROM orders
GROUP BY 1
ORDER BY 1;
```

**CTE for readability**
```sql
WITH active_users AS (
    SELECT id, name
    FROM users
    WHERE last_login >= NOW() - INTERVAL '30 days'
),
user_orders AS (
    SELECT
        user_id,
        COUNT(*) AS order_count,
        SUM(total) AS total_spent
    FROM orders
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY user_id
)
SELECT
    au.name,
    COALESCE(uo.order_count, 0) AS orders_last_30d,
    COALESCE(uo.total_spent, 0) AS spent_last_30d
FROM active_users au
LEFT JOIN user_orders uo ON uo.user_id = au.id
ORDER BY spent_last_30d DESC;
```

**Deduplication**
```sql
-- Keep the latest record per user
SELECT DISTINCT ON (user_id) *
FROM events
ORDER BY user_id, created_at DESC;
-- PostgreSQL only; use ROW_NUMBER() for MySQL/SQLite
```

**Pivot (conditional aggregation)**
```sql
SELECT
    product_id,
    SUM(CASE WHEN region = 'APAC' THEN revenue ELSE 0 END) AS apac_revenue,
    SUM(CASE WHEN region = 'EMEA' THEN revenue ELSE 0 END) AS emea_revenue,
    SUM(CASE WHEN region = 'AMER' THEN revenue ELSE 0 END) AS amer_revenue
FROM sales
GROUP BY product_id;
```

### Step 4: Performance Optimization

**Diagnose with EXPLAIN**
```sql
EXPLAIN ANALYZE
SELECT * FROM orders WHERE customer_id = 123;
-- Look for: Seq Scan (bad on large tables), hash join vs nested loop
```

**Index design**
```sql
-- Equality filter → single-column index
CREATE INDEX idx_orders_customer_id ON orders (customer_id);

-- Composite: put equality columns first, then range column
CREATE INDEX idx_orders_customer_date ON orders (customer_id, created_at DESC);

-- Partial index for common filters
CREATE INDEX idx_active_orders ON orders (customer_id)
WHERE status = 'active';
```

**Common performance fixes**
- Replace `SELECT *` with explicit column list
- Use `EXISTS` instead of `IN (SELECT ...)` for correlated subqueries
- Replace `OR` in WHERE with `UNION ALL` to allow index use
- Avoid functions on indexed columns in WHERE: use `WHERE created_at >= '2024-01-01'` not `WHERE YEAR(created_at) = 2024`
- Use `LIMIT` for exploratory queries on large tables

### Step 5: Output Format

For each query produced:
1. **The query** — formatted with consistent indentation (2 or 4 spaces, uppercase keywords)
2. **What it does** — one-line explanation
3. **Assumptions** — data model assumptions made
4. **Index suggestion** — if the query would benefit from an index
5. **Dialect notes** — flag syntax that differs between PostgreSQL / MySQL / SQLite
