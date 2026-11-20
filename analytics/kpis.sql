-- Analytical queries against the star schema produced by the pipeline.
-- Run them on the warehouse, e.g.:  sqlite3 data/processed/olist.db < analytics/kpis.sql
-- They show why the star schema is convenient: every KPI is a short join.

-- 1. Monthly revenue trend (product price + freight).
SELECT
    strftime('%Y-%m', order_purchase_timestamp) AS month,
    ROUND(SUM(total_item_value), 2)             AS revenue,
    COUNT(DISTINCT order_id)                     AS orders
FROM fact_order_items
GROUP BY month
ORDER BY month;

-- 2. Top 10 product categories by revenue (joins fact -> dim_products).
SELECT
    p.product_category,
    ROUND(SUM(f.total_item_value), 2) AS revenue,
    COUNT(*)                          AS items_sold
FROM fact_order_items f
JOIN dim_products p ON p.product_id = f.product_id
GROUP BY p.product_category
ORDER BY revenue DESC
LIMIT 10;

-- 3. On-time delivery rate by customer state (a data-quality / ops KPI).
SELECT
    c.customer_state,
    ROUND(100.0 * AVG(CASE WHEN f.is_late = 0 THEN 1 ELSE 0 END), 1) AS on_time_pct,
    ROUND(AVG(f.delivery_days), 1)                                    AS avg_delivery_days
FROM fact_order_items f
JOIN dim_customers c ON c.customer_id = f.customer_id
WHERE f.delivery_days IS NOT NULL
GROUP BY c.customer_state
ORDER BY on_time_pct DESC;

-- 4. Revenue by payment type (uses the new fact_payments table).
SELECT
    payment_type,
    ROUND(SUM(payment_value), 2) AS revenue,
    COUNT(*)                     AS payment_lines,
    ROUND(AVG(payment_installments), 1) AS avg_installments
FROM fact_payments
GROUP BY payment_type
ORDER BY revenue DESC;

-- 5. Customer satisfaction vs delivery lateness.
-- Relates the review score (dim_reviews, joined into the fact) to whether
-- the order arrived late — a direct ops/quality insight.
SELECT
    CASE WHEN is_late = 1 THEN 'late' ELSE 'on_time' END AS delivery,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    COUNT(*)                    AS items
FROM fact_order_items
WHERE review_score IS NOT NULL
GROUP BY is_late;

-- 6. Average review score by product category (fact -> dim_products + review).
SELECT
    p.product_category,
    ROUND(AVG(f.review_score), 2) AS avg_score,
    COUNT(*)                      AS reviewed_items
FROM fact_order_items f
JOIN dim_products p ON p.product_id = f.product_id
WHERE f.review_score IS NOT NULL
GROUP BY p.product_category
ORDER BY avg_score DESC;
