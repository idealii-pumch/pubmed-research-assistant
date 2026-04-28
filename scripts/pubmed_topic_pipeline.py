#!/usr/bin/env python
"""Fetch PubMed records from a final query, then filter, rank, and export a reading list."""

from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET

import pandas as pd

from grabpubmed import pubmed_utils

from pubmed_postprocess import process_pubmed_excel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the PubMed workflow from a confirmed query string to ranked outputs",
    )
    parser.add_argument("--query", required=True, help="Final PubMed query string")
    parser.add_argument("--topic", default="", help="Human-readable topic label for output naming")
    parser.add_argument(
        "--keywords",
        default="",
        help="Comma-separated ranking keywords. Default: derive from --topic or --query",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("NCBI_API_KEY") or os.environ.get("PUBMED_API_KEY") or "",
        help="NCBI API key. Default: read NCBI_API_KEY or PUBMED_API_KEY from environment",
    )
    parser.add_argument("--paper-type", default="Journal Article", help='PubMed publication type, e.g. "Journal Article"')
    parser.add_argument("--release-days", type=int, default=None, help="Limit PubMed fetch to the last N days")
    parser.add_argument("--grab-total", type=int, default=None, help="Maximum number of PubMed records to fetch")
    parser.add_argument("--output-dir", default="", help="Directory for final outputs")
    parser.add_argument(
        "--run-dir-name",
        default="",
        help="Preferred run directory name. Default: derived from --topic or --query",
    )
    parser.add_argument("--raw-xlsx", default="", help="Optional explicit path for the raw fetched xlsx")
    parser.add_argument("--jcr-path", default="", help="Optional JCR/CSA xlsx path for IF and quartile annotation")
    parser.add_argument("--years-back", type=int, default=None, help="Keep papers published in the last N years")
    parser.add_argument(
        "--start-date",
        default=None,
        help="Start date boundary: YYYY, YYYY-MM, YYYY-MM-DD, or natural words like today/now/至今",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="End date boundary: YYYY, YYYY-MM, YYYY-MM-DD, or natural words like today/now/至今",
    )
    parser.add_argument("--min-if", type=float, default=None, help="Minimum IF after annotation")
    parser.add_argument("--max-csa-quartile", type=int, default=None, help="Maximum CSA quartile (1 is best)")
    parser.add_argument(
        "--sort-by",
        choices=["date", "date_desc", "date_asc", "if", "if_desc", "keyword", "keyword_desc", "hybrid"],
        default="hybrid",
    )
    parser.add_argument("--w-date", type=float, default=0.4, help="Weight for date score in hybrid mode")
    parser.add_argument("--w-if", type=float, default=0.3, help="Weight for IF score in hybrid mode")
    parser.add_argument("--w-keyword", type=float, default=0.3, help="Weight for keyword hit score in hybrid mode")
    parser.add_argument("--top-n", type=int, default=150, help="Maximum number of ranked papers to keep")
    parser.add_argument(
        "--warn-count-threshold",
        type=int,
        default=200,
        help="Warn and stop when estimated retrieval count is above this threshold unless --allow-large-result is set",
    )
    parser.add_argument(
        "--allow-large-result",
        action="store_true",
        help="Continue even if estimated retrieval count exceeds --warn-count-threshold",
    )
    parser.add_argument(
        "--disable-real-pubdate-fix",
        action="store_true",
        help="Do not overwrite publish_date using PubMed ESummary PubDate",
    )
    return parser.parse_args()


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return cleaned[:80] or "pubmed_search"


def derive_keywords(explicit_keywords: str, topic: str, query: str) -> str:
    if explicit_keywords.strip():
        return explicit_keywords
    if topic.strip():
        return ",".join(part for part in re.split(r"[;/,]+", topic) if part.strip())
    candidate_terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", query)
    return ",".join(dict.fromkeys(candidate_terms[:12]))


def resolve_run_dir(output_dir: str, run_dir_name: str, topic: str, query: str) -> tuple[Path, str]:
    base_dir = Path(output_dir).expanduser().resolve() if output_dir else (Path.cwd() / "abstract").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    label = slugify(run_dir_name or topic or query)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_dir / label / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, label


def resolve_raw_xlsx(raw_xlsx: str, run_dir: Path, label: str) -> Path:
    if raw_xlsx:
        return Path(raw_xlsx).expanduser().resolve()
    return (run_dir / f"{label}_raw_query.xlsx").resolve()


def build_retrieval_query(query: str, paper_type: str) -> str:
    if not paper_type.strip():
        return query
    pub_type_filter = f'"{paper_type}"[Publication Type]'
    return f"({query}) AND ({pub_type_filter})"


def estimate_pubmed_count(query: str, paper_type: str, api_key: str | None) -> int | None:
    term = build_retrieval_query(query, paper_type)
    params = {
        "db": "pubmed",
        "retmode": "xml",
        "retmax": "0",
        "term": term,
    }
    if api_key:
        params["api_key"] = api_key
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(params)
    try:
        xml_text = urlopen(url, timeout=60).read()
        root = ET.fromstring(xml_text)
        count_text = root.findtext("Count")
        return int(count_text) if count_text else None
    except Exception as exc:
        print(f"Skip pre-count check due to error: {exc}")
        return None


def normalize_publish_date_from_pubmed(raw_xlsx: Path, api_key: str | None) -> tuple[int, int]:
    df = pd.read_excel(raw_xlsx)
    if "PMID" not in df.columns:
        print("Skip publish_date fix: PMID column not found.")
        return 0, 0

    pmids: list[str] = []
    for value in df["PMID"].dropna().tolist():
        try:
            pmids.append(str(int(float(value))))
        except (TypeError, ValueError):
            continue

    if not pmids:
        print("Skip publish_date fix: no valid PMID values.")
        return 0, 0

    pubdate_map: dict[str, str] = {}
    for i in range(0, len(pmids), 200):
        chunk = pmids[i : i + 200]
        params = {
            "db": "pubmed",
            "retmode": "xml",
            "id": ",".join(chunk),
        }
        if api_key:
            params["api_key"] = api_key
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urlencode(params)
        xml_text = urlopen(url, timeout=60).read()
        root = ET.fromstring(xml_text)
        for docsum in root.findall(".//DocSum"):
            pmid = docsum.findtext("Id")
            if not pmid:
                continue
            pub_date = ""
            for item in docsum.findall("Item"):
                if item.attrib.get("Name") == "PubDate":
                    pub_date = item.text or ""
                    break
            pubdate_map[pmid] = pub_date

    if "raw_publish_date" not in df.columns:
        df["raw_publish_date"] = df.get("publish_date", "")

    mapped = []
    replaced = 0
    for value in df["PMID"].tolist():
        try:
            pmid = str(int(float(value)))
        except (TypeError, ValueError):
            mapped.append(None)
            continue
        pub_date = pubdate_map.get(pmid)
        mapped.append(pub_date)
        if pub_date:
            replaced += 1

    df["publish_date"] = pd.Series(mapped, index=df.index).fillna(df.get("publish_date", ""))
    df.to_excel(raw_xlsx, index=False)
    return len(pmids), replaced


def build_query_log_text(
    *,
    run_dir: Path,
    query: str,
    retrieval_query: str,
    paper_type: str,
    estimated_count: int | None,
    raw_xlsx: Path,
    ranked_xlsx: Path,
    reading_list_html: Path,
    years_back: int | None,
    start_date: str | None,
    end_date: str | None,
    min_if: float | None,
    max_csa_quartile: int | None,
    sort_by: str,
    top_n: int,
) -> str:
    raw_df = pd.read_excel(raw_xlsx)
    ranked_df = pd.read_excel(ranked_xlsx)

    if_series = pd.to_numeric(raw_df.get("IF"), errors="coerce") if "IF" in raw_df.columns else pd.Series(dtype=float)
    q_series = (
        pd.to_numeric(raw_df.get("CSA_Quartile"), errors="coerce")
        if "CSA_Quartile" in raw_df.columns
        else pd.Series(dtype=float)
    )

    lines = [
        "QUERY_LOG_START",
        f"timestamp={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"query={query}",
        f"retrieval_query={retrieval_query}",
        f"paper_type={paper_type}",
        f"run_dir={run_dir}",
        f"raw_xlsx={raw_xlsx}",
        f"ranked_xlsx={ranked_xlsx}",
        f"html={reading_list_html}",
        f"estimated_retrieval_count={estimated_count if estimated_count is not None else 'N/A'}",
        f"fetched_total={len(raw_df)}",
        (
            "filter_sort: "
            f"years_back={years_back}; start_date={start_date}; end_date={end_date}; "
            f"min_if={min_if}; max_csa_quartile={max_csa_quartile}; sort_by={sort_by}; top_n={top_n}"
        ),
        f"raw_if_numeric_rows={int(if_series.notna().sum()) if len(if_series) else 0}",
        f"raw_q_numeric_rows={int(q_series.notna().sum()) if len(q_series) else 0}",
        f"raw_if_ge_10={int((if_series >= 10).sum()) if len(if_series) else 0}",
        f"raw_q_le_1={int((q_series <= 1).sum()) if len(q_series) else 0}",
        (
            f"raw_if_ge_10_and_q_le_1={int(((if_series >= 10) & (q_series <= 1)).sum())}"
            if len(if_series) and len(q_series)
            else "raw_if_ge_10_and_q_le_1=0"
        ),
        f"retained_rows={len(ranked_df)}",
        "retained_records:",
    ]

    retained_cols = [
        c
        for c in ["PMID", "Title", "Journal", "publish_date", "IF", "JCR_Quartile", "CSA_Quartile", "keyword_hits"]
        if c in ranked_df.columns
    ]
    if retained_cols and not ranked_df.empty:
        lines.append(ranked_df[retained_cols].to_string(index=False))
    else:
        lines.append("(empty)")

    lines.append("QUERY_LOG_END")
    return "\n".join(lines)


def write_and_print_query_log(log_text: str, run_dir: Path, label: str) -> Path:
    log_path = (run_dir / f"{label}_query_log.txt").resolve()
    log_path.write_text(log_text + "\n", encoding="utf-8")
    print(log_text)
    print(f"Saved query log: {log_path}")
    return log_path


def main() -> None:
    args = parse_args()
    keywords_text = derive_keywords(args.keywords, args.topic, args.query)
    run_dir, label = resolve_run_dir(args.output_dir, args.run_dir_name, args.topic, args.query)
    raw_xlsx = resolve_raw_xlsx(args.raw_xlsx, run_dir, label)
    raw_xlsx.parent.mkdir(parents=True, exist_ok=True)
    api_key = args.api_key.strip() or None

    estimated_count = estimate_pubmed_count(args.query, args.paper_type, api_key)
    if estimated_count is not None:
        print(f"Estimated retrieval count: {estimated_count}")
        if estimated_count > args.warn_count_threshold and not args.allow_large_result:
            raise SystemExit(
                "Estimated result count exceeds threshold. Refine query or rerun with --allow-large-result."
            )

    fetcher = pubmed_utils()
    retrieval_query = build_retrieval_query(args.query, args.paper_type)
    fetcher.get_main_info_into_excel(
        api_key,
        retrieval_query,
        args.release_days,
        "",
        args.grab_total,
        str(raw_xlsx),
    )

    if args.jcr_path:
        fetcher.embed_IF_into_excel(str(raw_xlsx), jcr_csa_path=args.jcr_path)
    else:
        default_jcr = (Path(__file__).resolve().parents[1] / "references" / "JCR_CSA_2025.xlsx").resolve()
        if default_jcr.exists():
            fetcher.embed_IF_into_excel(str(raw_xlsx), jcr_csa_path=str(default_jcr))
        else:
            print("Skip IF/CSA annotation: no --jcr-path provided and default JCR file not found.")

    if not args.disable_real_pubdate_fix:
        try:
            checked, replaced = normalize_publish_date_from_pubmed(raw_xlsx, api_key)
            print(f"publish_date fixed from PubMed ESummary for {replaced}/{checked} PMIDs")
        except Exception as exc:
            print(f"Skip publish_date fix due to error: {exc}")

    ranked_xlsx, reading_list_html = process_pubmed_excel(
        input_path=raw_xlsx,
        keywords_text=keywords_text,
        output_dir=str(run_dir),
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

    filtered_xlsx = ranked_xlsx.with_name(f"{label}_filtered_ranked.xlsx")
    filtered_html = reading_list_html.with_name(f"{label}_reading_list.html")
    if ranked_xlsx != filtered_xlsx:
        ranked_xlsx.replace(filtered_xlsx)
        ranked_xlsx = filtered_xlsx
    if reading_list_html != filtered_html:
        reading_list_html.replace(filtered_html)
        reading_list_html = filtered_html

    print(f"Saved raw xlsx: {raw_xlsx}")
    print(f"Saved ranked xlsx: {ranked_xlsx}")
    print(f"Saved html: {reading_list_html}")
    log_text = build_query_log_text(
        run_dir=run_dir,
        query=args.query,
        retrieval_query=retrieval_query,
        paper_type=args.paper_type,
        estimated_count=estimated_count,
        raw_xlsx=raw_xlsx,
        ranked_xlsx=ranked_xlsx,
        reading_list_html=reading_list_html,
        years_back=args.years_back,
        start_date=args.start_date,
        end_date=args.end_date,
        min_if=args.min_if,
        max_csa_quartile=args.max_csa_quartile,
        sort_by=args.sort_by,
        top_n=args.top_n,
    )
    write_and_print_query_log(log_text, run_dir, label)
    print(f"Run directory: {run_dir}")


if __name__ == "__main__":
    main()
