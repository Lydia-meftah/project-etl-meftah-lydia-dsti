"""Generate a self-contained KPI dashboard (HTML) from the warehouse.

Reads the SQLite warehouse produced by the pipeline, runs the KPI queries
and renders a single static HTML page (charts via Chart.js from a CDN). No
server needed — open the file in a browser.

Run:  python -m dashboard.build_dashboard   (or: make dashboard)
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from etl.config import DB_PATH

logger = logging.getLogger("dashboard")

OUTPUT_PATH = Path(__file__).resolve().parent / "dashboard.html"


def _query(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    return list(conn.execute(sql))


def collect_kpis(db_path: Path = DB_PATH) -> dict:
    """Run every KPI query and return a JSON-serialisable dict."""
    with sqlite3.connect(db_path) as conn:
        total_revenue = _query(
            conn, "SELECT ROUND(SUM(total_item_value), 2) FROM fact_order_items"
        )[0][0] or 0
        total_orders = _query(
            conn, "SELECT COUNT(DISTINCT order_id) FROM fact_order_items"
        )[0][0] or 0
        avg_score = _query(
            conn,
            "SELECT ROUND(AVG(review_score), 2) FROM fact_order_items "
            "WHERE review_score IS NOT NULL",
        )[0][0] or 0
        on_time_pct = _query(
            conn,
            "SELECT ROUND(100.0 * AVG(CASE WHEN is_late = 0 THEN 1 ELSE 0 END), 1) "
            "FROM fact_order_items WHERE delivery_days IS NOT NULL",
        )[0][0] or 0

        revenue_by_payment = _query(
            conn,
            "SELECT payment_type, ROUND(SUM(payment_value), 2) "
            "FROM fact_payments GROUP BY payment_type ORDER BY 2 DESC",
        )
        score_by_delivery = _query(
            conn,
            "SELECT CASE WHEN is_late = 1 THEN 'Late' ELSE 'On time' END, "
            "ROUND(AVG(review_score), 2) FROM fact_order_items "
            "WHERE review_score IS NOT NULL GROUP BY is_late",
        )
        monthly_revenue = _query(
            conn,
            "SELECT strftime('%Y-%m', order_purchase_timestamp), "
            "ROUND(SUM(total_item_value), 2) FROM fact_order_items "
            "GROUP BY 1 ORDER BY 1",
        )

    return {
        "cards": {
            "revenue": total_revenue,
            "orders": total_orders,
            "avg_score": avg_score,
            "on_time_pct": on_time_pct,
        },
        "revenue_by_payment": revenue_by_payment,
        "score_by_delivery": score_by_delivery,
        "monthly_revenue": monthly_revenue,
    }


def render_html(kpis: dict) -> str:
    """Embed the KPI data into a static HTML page."""
    data_json = json.dumps(kpis)
    return _TEMPLATE.replace("__DATA__", data_json)


def build(db_path: Path = DB_PATH, output: Path = OUTPUT_PATH) -> Path:
    kpis = collect_kpis(db_path)
    output.write_text(render_html(kpis), encoding="utf-8")
    logger.info("Dashboard written to %s", output)
    return output


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Olist Warehouse — KPI Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root { --bg:#0f172a; --card:#1e293b; --ink:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, sans-serif; background:var(--bg); color:var(--ink); padding:24px; }
  h1 { font-size:1.4rem; margin:0 0 4px; }
  p.sub { color:var(--muted); margin:0 0 24px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:24px; }
  .card { background:var(--card); border-radius:12px; padding:18px; }
  .card .label { color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; }
  .card .value { font-size:1.8rem; font-weight:700; margin-top:6px; }
  .charts { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }
  .chart { background:var(--card); border-radius:12px; padding:18px; }
  .chart h2 { font-size:.95rem; margin:0 0 12px; color:var(--ink); }
  footer { color:var(--muted); font-size:.75rem; margin-top:24px; }
</style>
</head>
<body>
  <h1>Olist Warehouse — KPI Dashboard</h1>
  <p class="sub">Generated from the star-schema warehouse built by the ETL pipeline.</p>
  <div class="cards" id="cards"></div>
  <div class="charts">
    <div class="chart"><h2>Revenue by payment type</h2><canvas id="payChart"></canvas></div>
    <div class="chart"><h2>Avg review score: on-time vs late</h2><canvas id="scoreChart"></canvas></div>
    <div class="chart"><h2>Monthly revenue</h2><canvas id="monthChart"></canvas></div>
  </div>
  <footer>Static page · data embedded at build time · refresh with <code>make dashboard</code>.</footer>
<script>
const K = __DATA__;
const fmt = n => new Intl.NumberFormat('en-US').format(n);
document.getElementById('cards').innerHTML = [
  ['Revenue', 'R$ ' + fmt(K.cards.revenue)],
  ['Orders', fmt(K.cards.orders)],
  ['Avg review score', K.cards.avg_score + ' / 5'],
  ['On-time delivery', K.cards.on_time_pct + ' %'],
].map(([l,v]) => `<div class="card"><div class="label">${l}</div><div class="value">${v}</div></div>`).join('');

const ACCENT = '#38bdf8';
const grid = { color:'rgba(148,163,184,.15)' }, ticks = { color:'#94a3b8' };
const opts = { plugins:{legend:{display:false}}, scales:{x:{grid,ticks},y:{grid,ticks}} };

new Chart(payChart, { type:'bar',
  data:{ labels:K.revenue_by_payment.map(r=>r[0]),
    datasets:[{ data:K.revenue_by_payment.map(r=>r[1]), backgroundColor:ACCENT }] }, options:opts });

new Chart(scoreChart, { type:'bar',
  data:{ labels:K.score_by_delivery.map(r=>r[0]),
    datasets:[{ data:K.score_by_delivery.map(r=>r[1]), backgroundColor:['#34d399','#f87171'] }] },
  options:{...opts, scales:{...opts.scales, y:{...opts.scales.y, min:0, max:5}}} });

new Chart(monthChart, { type:'line',
  data:{ labels:K.monthly_revenue.map(r=>r[0]),
    datasets:[{ data:K.monthly_revenue.map(r=>r[1]), borderColor:ACCENT, backgroundColor:'rgba(56,189,248,.2)', fill:true, tension:.3 }] },
  options:opts });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build()
