---
name: data-analysis
description: Analyze CSV and tabular data to generate insights, summaries, statistics, and visualizations. Handle data cleaning, aggregation, grouping, pivot tables, and outlier detection. Use when the user needs to analyze data, understand a dataset, find patterns, clean data, or generate a data summary.
license: Apache-2.0
metadata:
  author: anthropics
  version: "1.0"
  tags: [data-analysis, pandas, csv, statistics, insights, eda]
  platforms: [claude-code, cursor, any]
  triggers:
    - analyze this data
    - analyze this CSV
    - data analysis
    - summarize this dataset
    - find patterns in this data
    - clean this data
    - generate insights
    - exploratory data analysis
    - EDA
    - what does this data show
    - calculate statistics
---

# Data Analysis Skill

## Overview
Perform structured exploratory data analysis (EDA) on tabular datasets. Covers loading, cleaning, profiling, statistical analysis, grouping, and communicating insights clearly.

## Step-by-Step Process

### Step 1: Load and Inspect the Data

```python
import pandas as pd
import numpy as np

df = pd.read_csv("data.csv")

# Basic shape
print(f"Rows: {len(df):,}, Columns: {df.shape[1]}")
print(df.dtypes)
print(df.head(10))
```

For Excel: `pd.read_excel("data.xlsx", sheet_name=0)`
For JSON: `pd.read_json("data.json")`
For large files: use `pd.read_csv("data.csv", chunksize=10000)`

### Step 2: Profile the Dataset

```python
# Missing values
missing = df.isnull().sum()
print(missing[missing > 0])

# Descriptive statistics (numeric)
print(df.describe())

# Cardinality (categorical)
for col in df.select_dtypes("object").columns:
    print(f"{col}: {df[col].nunique()} unique values")
    if df[col].nunique() <= 20:
        print(df[col].value_counts())
```

### Step 3: Clean the Data

```python
# Drop duplicate rows
df = df.drop_duplicates()

# Handle missing values
df["column"].fillna(df["column"].median(), inplace=True)  # numeric
df["category"].fillna("Unknown", inplace=True)              # categorical

# Fix data types
df["date"] = pd.to_datetime(df["date"])
df["price"] = df["price"].str.replace("$", "").astype(float)

# Strip whitespace in strings
df["name"] = df["name"].str.strip()
```

### Step 4: Compute Key Statistics

```python
# Central tendency and spread
df["revenue"].agg(["mean", "median", "std", "min", "max"])

# Percentiles
df["revenue"].quantile([0.25, 0.5, 0.75, 0.9, 0.99])

# Correlation matrix
corr = df.select_dtypes("number").corr()
```

### Step 5: Group and Aggregate

```python
# Group by one dimension
summary = df.groupby("region")["revenue"].agg(["sum", "mean", "count"])

# Group by multiple dimensions
pivot = df.groupby(["year", "product_category"])["sales"].sum().unstack()

# Top N
top_products = df.groupby("product")["revenue"].sum().nlargest(10)
```

### Step 6: Detect Outliers

```python
# IQR method
Q1 = df["value"].quantile(0.25)
Q3 = df["value"].quantile(0.75)
IQR = Q3 - Q1
outliers = df[(df["value"] < Q1 - 1.5 * IQR) | (df["value"] > Q3 + 1.5 * IQR)]
print(f"Outliers: {len(outliers):,} rows ({len(outliers)/len(df):.1%})")
```

### Step 7: Time Series (If Applicable)

```python
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date").sort_index()

# Resample to monthly totals
monthly = df["revenue"].resample("ME").sum()

# Rolling average
df["revenue_7d_avg"] = df["revenue"].rolling(7).mean()
```

### Step 8: Communicate Findings

Structure your output as:
1. **Dataset Summary** — rows, columns, date range (if applicable)
2. **Data Quality** — missing values, duplicates, type issues found
3. **Key Metrics** — top-level numbers (total, average, growth rate)
4. **Patterns** — trends, segments, distributions worth noting
5. **Anomalies** — outliers or unexpected values
6. **Recommendations** — what to investigate further or act on

## Rules
- State units and time periods explicitly ("Average monthly revenue in USD, Jan–Dec 2024")
- Flag data quality issues before drawing conclusions
- Don't over-interpret: correlation ≠ causation
- Round to 2 significant figures for readability
- Prefer absolute numbers + percentages: "$1.2M revenue (↑23% YoY)"
