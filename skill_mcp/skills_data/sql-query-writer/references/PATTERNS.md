# SQL Query Patterns Reference

A reference for common SQL patterns: CTEs, window functions, aggregations, pagination, and performance optimization idioms.

---

## Common Table Expressions (CTEs)

### Basic CTE
```sql
WITH active_users AS (
    SELECT id, name, email
    FROM users
    WHERE last_login >= NOW() - INTERVAL '30 days'
        AND status = 'active'
)
SELECT * FROM active_users
ORDER BY name;
```

### Chained CTEs
```sql
WITH
raw_orders AS (
    SELECT customer_id, total, created_at
    FROM orders
    WHERE created_at >= '2024-01-01'
),
order_summary AS (
    SELECT
        customer_id,
        COUNT(*) AS order_count,
        SUM(total) AS revenue,
        AVG(total) AS avg_order_value
    FROM raw_orders
    GROUP BY customer_id
),
ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
    FROM order_summary
)
SELECT * FROM ranked WHERE revenue_rank <= 100;
```

### Recursive CTE (hierarchy traversal)
```sql
WITH RECURSIVE category_tree AS (
    -- Anchor: top-level categories
    SELECT id, name, parent_id, 0 AS depth, name::text AS path
    FROM categories
    WHERE parent_id IS NULL

    UNION ALL

    -- Recursive: children
    SELECT c.id, c.name, c.parent_id, ct.depth + 1, ct.path || ' > ' || c.name
    FROM categories c
    JOIN category_tree ct ON ct.id = c.parent_id
)
SELECT * FROM category_tree ORDER BY path;
```

---

## Window Functions

### ROW_NUMBER — Deduplication and top-N per group
```sql
-- Top 3 products by revenue per category
SELECT *
FROM (
    SELECT
        product_id,
        category_id,
        revenue,
        ROW_NUMBER() OVER (
            PARTITION BY category_id
            ORDER BY revenue DESC
        ) AS rank_in_category
    FROM product_sales
) ranked
WHERE rank_in_category <= 3;
```

### RANK vs DENSE_RANK
```sql
-- RANK leaves gaps: 1, 1, 3
-- DENSE_RANK has no gaps: 1, 1, 2
SELECT
    product_id,
    revenue,
    RANK() OVER (ORDER BY revenue DESC) AS rank_with_gaps,
    DENSE_RANK() OVER (ORDER BY revenue DESC) AS dense_rank
FROM product_sales;
```

### LAG / LEAD — Comparing adjacent rows
```sql
-- Month-over-month revenue change
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) AS prev_month_revenue,
    revenue - LAG(revenue, 1) OVER (ORDER BY month) AS mom_change,
    ROUND(
        (revenue - LAG(revenue, 1) OVER (ORDER BY month))::numeric
        / NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0) * 100,
        1
    ) AS mom_pct_change
FROM monthly_revenue
ORDER BY month;
```

### Running totals and moving averages
```sql
SELECT
    date,
    daily_revenue,
    SUM(daily_revenue) OVER (
        ORDER BY date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_revenue,
    AVG(daily_revenue) OVER (
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS revenue_7d_avg
FROM daily_sales;
```

### NTILE — Quartiles and percentiles
```sql
SELECT
    customer_id,
    revenue,
    NTILE(4) OVER (ORDER BY revenue) AS quartile,
    NTILE(100) OVER (ORDER BY revenue) AS percentile
FROM customer_revenue;
```

---

## Aggregation Patterns

### Conditional aggregation (pivot)
```sql
SELECT
    product_id,
    SUM(CASE WHEN region = 'APAC' THEN revenue ELSE 0 END) AS apac_revenue,
    SUM(CASE WHEN region = 'EMEA' THEN revenue ELSE 0 END) AS emea_revenue,
    SUM(CASE WHEN region = 'AMER' THEN revenue ELSE 0 END) AS amer_revenue,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM sales
GROUP BY product_id;
```

### FILTER clause (PostgreSQL / SQLite 3.30+)
```sql
-- Cleaner alternative to CASE WHEN for conditional aggregation
SELECT
    product_id,
    SUM(revenue) FILTER (WHERE region = 'APAC') AS apac_revenue,
    SUM(revenue) FILTER (WHERE region = 'EMEA') AS emea_revenue,
    COUNT(*) FILTER (WHERE status = 'refunded') AS refund_count
FROM sales
GROUP BY product_id;
```

### ROLLUP and CUBE (subtotals)
```sql
-- ROLLUP: subtotals at each level
SELECT
    COALESCE(region, 'ALL REGIONS') AS region,
    COALESCE(product_category, 'ALL CATEGORIES') AS category,
    SUM(revenue) AS total_revenue
FROM sales
GROUP BY ROLLUP (region, product_category)
ORDER BY region NULLS LAST, product_category NULLS LAST;
```

---

## Pagination Patterns

### Offset pagination (simple, less efficient at scale)
```sql
SELECT * FROM products
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 40;  -- page 3 of 20-per-page
```

### Cursor pagination (consistent, efficient for large tables)
```sql
-- First page
SELECT * FROM products
WHERE status = 'active'
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Next page (cursor = last row's created_at and id)
SELECT * FROM products
WHERE status = 'active'
    AND (created_at, id) < ('2024-03-15 10:30:00', 12345)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

---

## EXISTS vs IN vs JOIN

```sql
-- Prefer EXISTS for "does any match exist" checks
-- EXISTS stops on first match; IN fetches entire subquery result
SELECT * FROM orders o
WHERE EXISTS (
    SELECT 1 FROM order_items oi
    WHERE oi.order_id = o.id AND oi.product_id = 42
);

-- Prefer JOIN for bringing in columns from the related table
SELECT o.*, c.name AS customer_name
FROM orders o
JOIN customers c ON c.id = o.customer_id;

-- Use NOT EXISTS instead of NOT IN when the subquery can return NULL
-- NOT IN with any NULL in the subquery returns no rows!
SELECT * FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id
);
```

---

## Performance Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|---------|-----|
| `WHERE YEAR(created_at) = 2024` | Non-sargable: index unusable | `WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31'` |
| `WHERE LOWER(email) = 'x'` | Index unusable | Create functional index or use `citext` type |
| `SELECT *` in subquery | Fetches unnecessary columns | `SELECT 1` or specific columns |
| Correlated subquery in SELECT | Runs once per row | Rewrite as JOIN or window function |
| `OR` across indexed columns | May skip indexes | Rewrite as `UNION ALL` |
| `DISTINCT` without `ORDER BY` | Non-deterministic | Add explicit `ORDER BY` |
