# SQL Query Template — Standard Structure

Use this template when delivering SQL queries. Fill in each section.

---

## Query Description

**Purpose:** {One sentence describing what this query does}
**Target database:** {PostgreSQL | MySQL | SQLite | BigQuery | DuckDB}
**Tables involved:** `{table1}`, `{table2}`, `{table3}`

---

## Query

```sql
-- {Short description of what this block does}
WITH {cte_name} AS (
    SELECT
        {column_list}
    FROM {table}
    WHERE {conditions}
),

{another_cte} AS (
    SELECT
        {column_list}
    FROM {cte_name}
    JOIN {table} ON {join_condition}
    WHERE {conditions}
)

SELECT
    {final_column_list}
FROM {final_source}
WHERE {final_conditions}
ORDER BY {sort_column} {ASC|DESC}
LIMIT {n};
```

---

## Explanation

### What It Does
{1-2 paragraph explanation of the query logic, step by step}

### Assumptions
- **{assumption_1}:** e.g., "The `status` column uses string values 'active' and 'inactive'"
- **{assumption_2}:** e.g., "Dates are stored in UTC in a `timestamptz` column"
- **{assumption_3}:** e.g., "orders.customer_id is a foreign key referencing customers.id"

---

## Performance Notes

### Recommended Indexes

```sql
-- Index for the primary filter condition
CREATE INDEX idx_{table}_{column} ON {table} ({column});

-- Composite index if filtering on multiple columns together
CREATE INDEX idx_{table}_{col1}_{col2} ON {table} ({col1}, {col2} DESC);
```

### Estimated Performance
- **Row count:** ~{N} rows expected in result
- **Scans:** {Seq Scan / Index Scan} on `{table}` ({size_estimate})
- **Run EXPLAIN ANALYZE to verify:**

```sql
EXPLAIN ANALYZE
{paste query here};
```

---

## Dialect Notes

| Feature | PostgreSQL | MySQL | SQLite |
|---------|-----------|-------|--------|
| Window functions | ✅ Full support | ✅ 8.0+ | ✅ 3.25+ |
| `FILTER` clause | ✅ | ❌ Use `CASE WHEN` | ✅ 3.30+ |
| `DISTINCT ON` | ✅ | ❌ Use ROW_NUMBER() | ❌ Use ROW_NUMBER() |
| `INTERVAL` syntax | `INTERVAL '7 days'` | `INTERVAL 7 DAY` | `date('now', '-7 days')` |

{Note any specific syntax that differs for the target dialect}

---

## Sample Result

| {col1} | {col2} | {col3} |
|--------|--------|--------|
| {val}  | {val}  | {val}  |
| {val}  | {val}  | {val}  |
