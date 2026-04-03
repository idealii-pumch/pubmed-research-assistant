#!/usr/bin/env python
"""Post-process PubMed Excel output: filter, rank, and export interactive HTML."""

from __future__ import annotations

import argparse
import html
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


COL_ALIASES = {
    "title": ["Title", "title"],
    "abstract": ["Abstract", "abstract"],
    "date": ["publish_date", "PublishDate", "Date", "PubDate"],
    "if": ["IF", "ImpactFactor", "impact_factor"],
    "quartile": ["CSA_Quartile", "Quartile", "CAS_Quartile"],
    "pmid": ["PMID", "pmid"],
    "journal": ["Journal", "journal"],
    "doi": ["DOI", "doi"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter and rank PubMed results, then export HTML")
    parser.add_argument("--input", required=True, help="Input xlsx path from PubMed pipeline")
    parser.add_argument("--keywords", required=True, help="Comma-separated query keywords")
    parser.add_argument("--output-dir", default="", help="Output directory (default: abstract/<topic>_<timestamp>)")
    parser.add_argument("--years-back", type=int, default=None, help="Keep papers published in last N years")
    parser.add_argument("--start-date", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--min-if", type=float, default=None, help="Minimum IF")
    parser.add_argument("--max-csa-quartile", type=int, default=None, help="Maximum CSA quartile (1 is best)")
    parser.add_argument("--sort-by", choices=["date", "if", "keyword", "hybrid"], default="hybrid")
    parser.add_argument("--w-date", type=float, default=0.4, help="Weight for date score in hybrid mode")
    parser.add_argument("--w-if", type=float, default=0.3, help="Weight for IF score in hybrid mode")
    parser.add_argument("--w-keyword", type=float, default=0.3, help="Weight for keyword hit score in hybrid mode")
    parser.add_argument("--top-n", type=int, default=150, help="Max number of records after ranking")
    return parser.parse_args()


def resolve_output_paths(input_path: Path, output_dir: str = "") -> tuple[Path, Path, Path]:
    base = input_path.stem
    if output_dir:
        out_dir = Path(output_dir).expanduser().resolve()
    else:
        abstract_root = Path.cwd() / "abstract"
        abstract_root.mkdir(parents=True, exist_ok=True)
        run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_base = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_") or "pubmed"
        out_dir = abstract_root / f"{safe_base}_{run_tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir, out_dir / f"{base}_ranked.xlsx", out_dir / f"{base}_reading_list.html"


def pick_col(df: pd.DataFrame, logical_name: str) -> str | None:
    for candidate in COL_ALIASES[logical_name]:
        if candidate in df.columns:
            return candidate
    return None


def parse_keywords(text: str) -> list[str]:
    kws = [k.strip().lower() for k in text.split(",") if k.strip()]
    return list(dict.fromkeys(kws))


def parse_pub_date_series(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    ymd_mask = s.str.fullmatch(r"\d{8}")
    parsed_ymd = pd.to_datetime(s.where(ymd_mask), format="%Y%m%d", errors="coerce")
    parsed_fallback = pd.to_datetime(s.where(~ymd_mask), errors="coerce")
    out = parsed_ymd.fillna(parsed_fallback)
    return out


def count_hits(text: str, keywords: Iterable[str]) -> int:
    if not isinstance(text, str) or not text.strip():
        return 0
    hay = text.lower()
    total = 0
    for kw in keywords:
        total += len(re.findall(re.escape(kw), hay))
    return total


def normalize(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0.0)
    min_v, max_v = float(s.min()), float(s.max())
    if math.isclose(min_v, max_v):
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - min_v) / (max_v - min_v)


def format_date(x) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, str):
        return x
    try:
        return pd.to_datetime(x).strftime("%Y-%m-%d")
    except Exception:
        return str(x)


def build_highlighter(keywords: list[str]):
    tokens = [k.strip() for k in keywords if k.strip()]
    if not tokens:
        return lambda s: s
    tokens = sorted(set(tokens), key=len, reverse=True)
    pattern = re.compile(r"(?i)(" + "|".join(re.escape(t) for t in tokens) + r")")
    return lambda s: pattern.sub(lambda m: f"<mark class='kw'>{m.group(0)}</mark>", s)


def render_html(df: pd.DataFrame, out_html: Path, query_keywords: list[str], query_info: dict, cols: dict):
    highlighter = build_highlighter(query_keywords)
    storage_suffix = re.sub(r"[^a-zA-Z0-9_]", "_", out_html.stem)[:64]

    sidebar_links = []
    cards = []

    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        title_raw = str(row.get(cols["title"], ""))
        abstract_raw = str(row.get(cols["abstract"], ""))
        pmid = str(row.get(cols["pmid"], "")) if cols["pmid"] else ""
        journal = str(row.get(cols["journal"], "")) if cols["journal"] else ""
        doi = str(row.get(cols["doi"], "")) if cols["doi"] else ""
        pdate = format_date(row.get("_date", ""))
        ifv = row.get(cols["if"], "") if cols["if"] else ""
        kw_hits = row.get("keyword_hits", "")

        article_id = f"article-{rank}"
        bookmark_text = f"{journal or 'Unknown Journal'}. {pdate or 'Unknown Date'}"
        sidebar_links.append(
            f"<li><a href='#{article_id}' data-article-id='{article_id}'><span class='bookmark-indicators' id='ind-{article_id}'></span>{html.escape(bookmark_text)}</a></li>"
        )

        safe_title = html.escape(title_raw)
        safe_abstract = html.escape(abstract_raw)
        highlighted_title = highlighter(safe_title)
        highlighted_abstract = highlighter(safe_abstract)
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid and pmid != "nan" else ""

        cards.append(
            f"""
            <article class='paper' id='{article_id}'>
              <div class='paper-actions'>
                <button class='action-btn star-btn' onclick="toggleStar('{article_id}')" title='星标'>⭐</button>
                <button class='action-btn read-btn' onclick="toggleRead('{article_id}')" title='已读'>✓</button>
              </div>
              <h3>{rank}. {highlighted_title}</h3>
              <div class='meta'>Date: {html.escape(pdate)} | IF: {html.escape(str(ifv))} | KeywordHits: {html.escape(str(kw_hits))} | Journal: {html.escape(journal)}</div>
              <div class='meta'>PMID: <a href='{html.escape(link)}' target='_blank'>{html.escape(pmid)}</a> | DOI: {html.escape(doi)}</div>
              <p>{highlighted_abstract}</p>
            </article>
            """
        )

    html_content = f"""
<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>PubMed Reading List</title>
<style>
:root {{
  --bg: #f8fafc;
  --panel: #ffffff;
  --text: #0f172a;
  --muted: #475569;
  --border: #e2e8f0;
  --accent: #0f766e;
  --kw-bg: #fff3a3;
  --kw-text: #5f370e;
}}
body[data-theme='dark'] {{
  --bg: #0b1220;
  --panel: #111827;
  --text: #e5e7eb;
  --muted: #9ca3af;
  --border: #1f2937;
  --accent: #5eead4;
  --kw-bg: #6b21a8;
  --kw-text: #f5d0fe;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: var(--bg); color: var(--text); transition: background .2s,color .2s,padding-left .2s; padding-left: 290px; }}
body.sidebar-closed {{ padding-left: 0; }}
.sidebar {{ position: fixed; left: 0; top: 0; width: 280px; height: 100vh; overflow-y: auto; background: var(--panel); border-right: 1px solid var(--border); padding: 16px; transform: translateX(0); transition: transform .2s; z-index: 20; }}
.sidebar.hidden {{ transform: translateX(-280px); }}
.sidebar h2 {{ margin: 0 0 12px 0; font-size: 1rem; color: var(--accent); }}
.sidebar ul {{ margin: 0; padding: 0; list-style: none; }}
.sidebar li {{ margin: 6px 0; }}
.sidebar a {{ color: var(--muted); text-decoration: none; font-size: .92rem; display: flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 8px; }}
.sidebar a:hover {{ background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--text); }}
.sidebar-controls {{ display: flex; gap: 8px; margin-bottom: 10px; }}
.icon-btn {{ border: 1px solid var(--border); background: var(--panel); color: var(--text); border-radius: 8px; padding: 6px 10px; cursor: pointer; }}
.sidebar-toggle {{ position: fixed; left: 292px; top: 12px; z-index: 30; }}
.sidebar-toggle.sidebar-hidden {{ left: 12px; }}
.container {{ max-width: 1080px; margin: 0 auto; padding: 16px; }}
.paper {{ position: relative; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 12px; }}
.paper h3 {{ margin: 0 90px 8px 0; }}
.paper-actions {{ position: absolute; top: 10px; right: 10px; display: flex; gap: 6px; }}
.action-btn {{ border: 1px solid var(--border); background: transparent; color: var(--muted); border-radius: 8px; padding: 4px 8px; cursor: pointer; }}
.action-btn.active {{ color: var(--text); border-color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); }}
.paper.starred {{ border-left: 4px solid #eab308; }}
.paper.read {{ opacity: 0.7; }}
.meta {{ color: var(--muted); font-size: .9rem; margin: 3px 0; }}
p {{ line-height: 1.55; white-space: pre-wrap; }}
a {{ color: var(--accent); }}
mark.kw {{ background: var(--kw-bg); color: var(--kw-text); border-radius: 3px; padding: 0 2px; }}
.bookmark-indicators {{ display: inline-flex; min-width: 26px; gap: 2px; }}
</style>
</head>
<body data-theme='light'>
<button class='icon-btn sidebar-toggle' onclick='toggleSidebar()'>☰</button>
<aside class='sidebar' id='sidebar'>
  <h2>Bookmarks</h2>
  <div class='sidebar-controls'>
    <button class='icon-btn' onclick='toggleTheme()' id='theme-btn'>🌙 Dark</button>
  </div>
  <ul>
    {''.join(sidebar_links)}
  </ul>
</aside>
<main class='container'>
  {''.join(cards)}
</main>
<script>
const KEY = '{storage_suffix}';
const STAR_K = 'starred_' + KEY;
const READ_K = 'read_' + KEY;
const THEME_K = 'theme_' + KEY;

function getList(k) {{
  try {{ return JSON.parse(localStorage.getItem(k) || '[]'); }} catch(e) {{ return []; }}
}}
function setList(k, v) {{ localStorage.setItem(k, JSON.stringify(v)); }}

function updateIndicators(articleId) {{
  const node = document.getElementById('ind-' + articleId);
  if (!node) return;
  const stars = getList(STAR_K);
  const reads = getList(READ_K);
  let html = '';
  if (stars.includes(articleId)) html += '<span>⭐</span>';
  if (reads.includes(articleId)) html += '<span>✓</span>';
  node.innerHTML = html;
}}

function updateCardState(articleId) {{
  const card = document.getElementById(articleId);
  if (!card) return;
  const stars = getList(STAR_K);
  const reads = getList(READ_K);
  const starBtn = card.querySelector('.star-btn');
  const readBtn = card.querySelector('.read-btn');

  card.classList.toggle('starred', stars.includes(articleId));
  card.classList.toggle('read', reads.includes(articleId));
  if (starBtn) starBtn.classList.toggle('active', stars.includes(articleId));
  if (readBtn) readBtn.classList.toggle('active', reads.includes(articleId));
  updateIndicators(articleId);
}}

function toggleStar(articleId) {{
  const stars = getList(STAR_K);
  const i = stars.indexOf(articleId);
  if (i >= 0) stars.splice(i, 1); else stars.push(articleId);
  setList(STAR_K, stars);
  updateCardState(articleId);
}}

function toggleRead(articleId) {{
  const reads = getList(READ_K);
  const i = reads.indexOf(articleId);
  if (i >= 0) reads.splice(i, 1); else reads.push(articleId);
  setList(READ_K, reads);
  updateCardState(articleId);
}}

function toggleSidebar() {{
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  document.body.classList.toggle('sidebar-closed');
  sidebar.classList.toggle('hidden');
  toggle.classList.toggle('sidebar-hidden');
}}

function applyTheme(theme) {{
  const t = theme === 'dark' ? 'dark' : 'light';
  document.body.setAttribute('data-theme', t);
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = t === 'dark' ? '☀ Light' : '🌙 Dark';
}}

function toggleTheme() {{
  const cur = localStorage.getItem(THEME_K) || 'light';
  const next = cur === 'light' ? 'dark' : 'light';
  localStorage.setItem(THEME_K, next);
  applyTheme(next);
}}

window.addEventListener('DOMContentLoaded', () => {{
  applyTheme(localStorage.getItem(THEME_K) || 'light');
  document.querySelectorAll('.paper').forEach(card => updateCardState(card.id));
}});
</script>
</body>
</html>
"""

    out_html.write_text(html_content, encoding="utf-8")


def process_pubmed_excel(
    input_path: str | Path,
    keywords_text: str,
    output_dir: str = "",
    years_back: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_if: float | None = None,
    max_csa_quartile: int | None = None,
    sort_by: str = "hybrid",
    w_date: float = 0.4,
    w_if: float = 0.3,
    w_keyword: float = 0.3,
    top_n: int = 150,
) -> tuple[Path, Path]:
    in_path = Path(input_path).expanduser().resolve()
    if not in_path.exists():
        raise FileNotFoundError(f"Input not found: {in_path}")

    _, out_xlsx, out_html = resolve_output_paths(in_path, output_dir)
    df = pd.read_excel(in_path)

    cols = {k: pick_col(df, k) for k in COL_ALIASES}
    if not cols["title"] or not cols["abstract"]:
        raise ValueError("Missing required columns: Title/Abstract")

    keywords = parse_keywords(keywords_text)
    if not keywords:
        raise ValueError("No valid keywords from --keywords")

    if cols["date"]:
        df["_date"] = parse_pub_date_series(df[cols["date"]])
        if years_back is not None:
            cutoff = pd.Timestamp(datetime.today()) - pd.DateOffset(years=years_back)
            df = df[df["_date"] >= cutoff]
        if start_date:
            df = df[df["_date"] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df["_date"] <= pd.to_datetime(end_date)]
    else:
        df["_date"] = pd.NaT

    if min_if is not None and cols["if"]:
        df = df[pd.to_numeric(df[cols["if"]], errors="coerce") >= min_if]

    if max_csa_quartile is not None and cols["quartile"]:
        df = df[pd.to_numeric(df[cols["quartile"]], errors="coerce") <= max_csa_quartile]

    df = df.copy()
    df["title_keyword_hits"] = df[cols["title"]].astype(str).map(lambda t: count_hits(t, keywords))
    df["abstract_keyword_hits"] = df[cols["abstract"]].astype(str).map(lambda t: count_hits(t, keywords))
    df["keyword_hits"] = df["title_keyword_hits"] + df["abstract_keyword_hits"]

    df["_date_ord"] = pd.to_datetime(df["_date"], errors="coerce").map(lambda x: x.toordinal() if pd.notna(x) else 0)
    df["_if_num"] = pd.to_numeric(df[cols["if"]], errors="coerce") if cols["if"] else 0

    if sort_by == "date":
        df = df.sort_values(["_date_ord", "keyword_hits"], ascending=[False, False])
    elif sort_by == "if":
        df = df.sort_values(["_if_num", "keyword_hits", "_date_ord"], ascending=[False, False, False])
    elif sort_by == "keyword":
        df = df.sort_values(["keyword_hits", "_if_num", "_date_ord"], ascending=[False, False, False])
    else:
        wsum = w_date + w_if + w_keyword
        if wsum <= 0:
            raise ValueError("Hybrid weights must sum to > 0")
        wd, wi, wk = w_date / wsum, w_if / wsum, w_keyword / wsum
        df["_score"] = wd * normalize(df["_date_ord"]) + wi * normalize(df["_if_num"]) + wk * normalize(df["keyword_hits"])
        df = df.sort_values(["_score", "keyword_hits"], ascending=[False, False])

    if top_n and top_n > 0:
        df = df.head(top_n)

    df.to_excel(out_xlsx, index=False)

    query_info = {
        "sort_by": sort_by,
        "years_back": years_back,
        "start_date": start_date,
        "end_date": end_date,
        "min_if": min_if,
        "max_csa_quartile": max_csa_quartile,
        "weights": {"date": w_date, "if": w_if, "keyword": w_keyword},
    }
    render_html(df, out_html, keywords, query_info, cols)
    return out_xlsx, out_html


def main() -> None:
    args = parse_args()
    out_xlsx, out_html = process_pubmed_excel(
        input_path=args.input,
        keywords_text=args.keywords,
        output_dir=args.output_dir,
        years_back=args.years_back,
        start_date=args.start_date,
        end_date=args.end_date,
        min_if=args.min_if,
        max_csa_quartile=args.max_csa_quartile,
        sort_by=args.sort_by,
        w_date=args.w_date,
        w_if=args.w_if,
        w_keyword=args.w_keyword,
        top_n=args.top_n,
    )
    print(f"Saved ranked xlsx: {out_xlsx}")
    print(f"Saved html: {out_html}")


if __name__ == "__main__":
    main()
