# ADPA Minimal ETL Requirements

## Objectives
- Land raw data in S3 and register in Glue Catalog for Athena querying.
- Produce a curated sales facts table joined with users, plus a clean events table.

## Ingestion
- Sources: CSV (sales), JSONL (users), Parquet (events), CSV.GZ (logs).
- Location: s3://<RAW_BUCKET>/adpa/raw/*

## Transformations (Raw → Curated)
1. **sales_clean**
   - Cast types (quantity:int, unit_price:double, order_date:date).
   - Drop negative quantity or unit_price.
   - Derive `revenue = quantity * unit_price` (already present; recompute if missing).

2. **users_clean**
   - Lowercase email; drop rows missing user_id or email.
   - Deduplicate on `user_id` keeping latest `signup_ts`.

3. **events_clean**
   - Keep `event_type` in {view, click, add_to_cart, purchase}; otherwise map to `other`.
   - Filter out rows with null `user_id`.

4. **fact_sales_by_user**
   - Join `sales_clean` ↔ `users_clean` on `customer_id = user_id`.
   - Partition by `order_date` in `s3://<CURATED_BUCKET>/adpa/curated/fact_sales_by_user/`.

## Output
- Curated tables in S3 (Parquet, snappy):
  - `s3://<CURATED_BUCKET>/adpa/curated/sales_clean/`
  - `s3://<CURATED_BUCKET>/adpa/curated/users_clean/`
  - `s3://<CURATED_BUCKET>/adpa/curated/events_clean/`
  - `s3://<CURATED_BUCKET>/adpa/curated/fact_sales_by_user/`

## Orchestration
- Minimal: EventBridge → Lambda placeholder (copy/transform).
- Future: Step Functions or Glue ETL jobs for heavy transforms.

## Observability
- Lambda logs in CloudWatch.
- Add custom metrics later (row counts, error rate).