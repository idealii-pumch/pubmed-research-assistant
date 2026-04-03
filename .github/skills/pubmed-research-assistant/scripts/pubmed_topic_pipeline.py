#!/usr/bin/env python
"""Fetch PubMed records from a final query, then filter, rank, and export a reading list."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

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
    parser.add_argument("--raw-xlsx", default="", help="Optional explicit path for the raw fetched xlsx")
    parser.add_argument("--jcr-path", default="", help="Optional JCR/CSA xlsx path for IF and quartile annotation")
    parser.add_argument("--years-back", type=int, default=None, help="Keep papers published in the last N years")
    parser.add_argument("--start-date", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--min-if", type=float, default=None, help="Minimum IF after annotation")
    parser.add_argument("--max-csa-quartile", type=int, default=None, help="Maximum CSA quartile (1 is best)")
    parser.add_argument("--sort-by", choices=["date", "if", "keyword", "hybrid"], default="hybrid")
    parser.add_argument("--w-date", type=float, default=0.4, help="Weight for date score in hybrid mode")
    parser.add_argument("--w-if", type=float, default=0.3, help="Weight for IF score in hybrid mode")
    parser.add_argument("--w-keyword", type=float, default=0.3, help="Weight for keyword hit score in hybrid mode")
    parser.add_argument("--top-n", type=int, default=150, help="Maximum number of ranked papers to keep")
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


def resolve_raw_xlsx(raw_xlsx: str, topic: str, query: str) -> Path:
    if raw_xlsx:
        return Path(raw_xlsx).expanduser().resolve()
    abstract_root = Path.cwd() / "abstract"
    abstract_root.mkdir(parents=True, exist_ok=True)
    label = slugify(topic or query)
    return (abstract_root / f"{label}.xlsx").resolve()


def main() -> None:
    args = parse_args()
    keywords_text = derive_keywords(args.keywords, args.topic, args.query)
    raw_xlsx = resolve_raw_xlsx(args.raw_xlsx, args.topic, args.query)
    raw_xlsx.parent.mkdir(parents=True, exist_ok=True)

    fetcher = pubmed_utils()
    fetcher.get_main_info_into_excel(
        args.api_key,
        args.query,
        args.release_days,
        args.paper_type,
        args.grab_total,
        str(raw_xlsx),
    )

    if args.jcr_path:
        fetcher.embed_IF_into_excel(str(raw_xlsx), jcr_csa_path=args.jcr_path)
    else:
        default_jcr = Path(r"E:\Python\GrabPubmed\JCR_CSA_2025.xlsx")
        if default_jcr.exists():
            fetcher.embed_IF_into_excel(str(raw_xlsx), jcr_csa_path=str(default_jcr))
        else:
            print("Skip IF/CSA annotation: no --jcr-path provided and default JCR file not found.")

    ranked_xlsx, reading_list_html = process_pubmed_excel(
        input_path=raw_xlsx,
        keywords_text=keywords_text,
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

    print(f"Saved raw xlsx: {raw_xlsx}")
    print(f"Saved ranked xlsx: {ranked_xlsx}")
    print(f"Saved html: {reading_list_html}")


if __name__ == "__main__":
    main()
