#!/usr/bin/env python
"""Fetch PubMed records with stdlib only, emit CSV-friendly records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import urlopen
import xml.etree.ElementTree as ET

import pandas as pd


_MONTH_MAP = {
    "jan": "01",
    "feb": "02",
    "mar": "03",
    "apr": "04",
    "may": "05",
    "jun": "06",
    "jul": "07",
    "aug": "08",
    "sep": "09",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}


def _text_or_empty(value: str | None) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_month(raw: str | None) -> str:
    if not raw:
        return ""
    s = raw.strip()
    if s.isdigit():
        return s.zfill(2)
    key = s[:3].lower()
    return _MONTH_MAP.get(key, s)


def _parse_pub_date(pub_date_el: ET.Element | None) -> str:
    if pub_date_el is None:
        return ""
    medline_date = _text_or_empty(pub_date_el.findtext("MedlineDate"))
    if medline_date:
        return medline_date

    year = _text_or_empty(pub_date_el.findtext("Year"))
    month = _normalize_month(_text_or_empty(pub_date_el.findtext("Month")))
    day = _text_or_empty(pub_date_el.findtext("Day"))

    if year and month and day:
        return f"{year}-{month}-{day.zfill(2)}"
    if year and month:
        return f"{year}-{month}"
    return year


def _build_abstract_text(article_el: ET.Element) -> str:
    abstract_el = article_el.find(".//Abstract")
    if abstract_el is None:
        return ""

    parts: list[str] = []
    for item in abstract_el.findall("AbstractText"):
        label = item.attrib.get("Label", "")
        raw = "".join(item.itertext())
        text = _text_or_empty(raw)
        if label and text:
            parts.append(f"{label}: {text}")
        elif text:
            parts.append(text)
    return "\n".join(parts)


def _extract_doi(article_el: ET.Element) -> str:
    for article_id in article_el.findall(".//ArticleIdList/ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            return _text_or_empty(article_id.text)
    return ""


@dataclass
class PubmedFetchResult:
    total: int
    records: list[dict[str, str]]


class PubmedFetcher:
    def __init__(self) -> None:
        pass

    def _get_xml(self, base_url: str, params: dict[str, str | int]) -> ET.Element:
        url = base_url + "?" + urlencode(params)
        xml_text = urlopen(url, timeout=60).read()
        return ET.fromstring(xml_text)

    def _esearch(self, api_key: str | None, term: str, release_days: int | None) -> tuple[int, str, str]:
        params: dict[str, str | int] = {
            "db": "pubmed",
            "term": term,
            "usehistory": "y",
            "retmax": 0,
            "retmode": "xml",
        }
        if api_key:
            params["api_key"] = api_key
        if release_days:
            params["reldate"] = release_days

        root = self._get_xml("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params)
        total = int(root.findtext("Count") or 0)
        webenv = _text_or_empty(root.findtext("WebEnv"))
        query_key = _text_or_empty(root.findtext("QueryKey"))
        return total, webenv, query_key

    def _fetch_batch(
        self,
        api_key: str | None,
        webenv: str,
        query_key: str,
        retstart: int,
        retmax: int,
    ) -> Iterable[ET.Element]:
        params: dict[str, str | int] = {
            "db": "pubmed",
            "retmode": "xml",
            "rettype": "abstract",
            "retstart": retstart,
            "retmax": retmax,
            "webenv": webenv,
            "query_key": query_key,
        }
        if api_key:
            params["api_key"] = api_key

        root = self._get_xml("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params)
        return root.findall(".//PubmedArticle")

    def get_main_info_into_csv(
        self,
        api_key: str | None,
        search_term: str,
        release_date_cutoff: int | None,
        grab_total: int | None,
        save_path: str,
    ) -> PubmedFetchResult:
        total, webenv, query_key = self._esearch(api_key, search_term, release_date_cutoff)
        if not webenv or not query_key:
            raise RuntimeError("PubMed ESearch returned empty history tokens.")

        if grab_total is None or grab_total > total:
            grab_total = total

        batch_size = 200
        records: list[dict[str, str]] = []
        fetched = 0

        while fetched < grab_total:
            retmax = min(batch_size, grab_total - fetched)
            for article in self._fetch_batch(api_key, webenv, query_key, fetched, retmax):
                pmid = _text_or_empty(article.findtext(".//MedlineCitation/PMID"))
                article_el = article.find(".//Article")
                if article_el is None:
                    continue
                title = _text_or_empty(article_el.findtext("ArticleTitle"))
                journal_abbr = _text_or_empty(article.findtext(".//MedlineJournalInfo/MedlineTA"))
                journal = _text_or_empty(article_el.findtext("Journal/Title"))
                if not journal:
                    journal = journal_abbr

                pub_date = _parse_pub_date(article_el.find("Journal/JournalIssue/PubDate"))
                abstract = _build_abstract_text(article_el)
                doi = _extract_doi(article_el)

                records.append(
                    {
                        "PMID": pmid,
                        "Title": title,
                        "Journal": journal,
                        "Journal_Abbr": journal_abbr,
                        "publish_date": pub_date,
                        "Abstract": abstract,
                        "DOI": doi,
                    }
                )
            fetched += retmax
            time.sleep(0.34)

        df = pd.DataFrame(records)
        df.to_csv(save_path, index=False)
        return PubmedFetchResult(total=total, records=records)

    def embed_if_into_csv(self, csv_path: str, jcr_csa_path: str) -> None:
        dtype_spec = {
            "CAS_Quartile": "string",
            "JIF_Quartile": "string",
            "JIF_2024": "string",
            "ISSN": "string",
            "eISSN": "string",
        }
        jcr_df = pd.read_csv(jcr_csa_path, dtype=dtype_spec)

        jcr_lookup: dict[str, dict[str, str]] = {}
        for _, row in jcr_df.iterrows():
            med_abbr = row.get("MedAbbr")
            if pd.notna(med_abbr):
                key = str(med_abbr).strip().upper()
                jcr_lookup[key] = {
                    "JIF_2024": row.get("JIF_2024", "N/A"),
                    "JIF_Quartile": row.get("JIF_Quartile", "N/A"),
                    "CAS_Quartile": row.get("CAS_Quartile", "N/A"),
                }

        query_df = pd.read_csv(csv_path)
        cols_to_drop = ["IF", "JCR_Quartile", "CSA_Quartile", "Top", "Open Access"]
        existing_cols = [col for col in cols_to_drop if col in query_df.columns]
        if existing_cols:
            query_df = query_df.drop(columns=existing_cols)

        jif_list: list[str] = []
        jif_quartile_list: list[str] = []
        cas_quartile_list: list[str] = []

        for _, row in query_df.iterrows():
            # 优先用 NLM 缩写匹配 JCR 的 MedAbbr
            journal_abbr = row.get("Journal_Abbr")
            journal_name = row.get("Journal")
            journal_key = str(journal_abbr).strip().upper() if pd.notna(journal_abbr) and str(journal_abbr).strip() else ""
            if not journal_key and pd.notna(journal_name):
                journal_key = str(journal_name).strip().upper()
            if not journal_key:
                jif_list.append("N/A")
                jif_quartile_list.append("N/A")
                cas_quartile_list.append("N/A")
                continue
            if journal_key in jcr_lookup:
                match_info = jcr_lookup[journal_key]
                jif_list.append(str(match_info.get("JIF_2024", "N/A")))
                jif_quartile_list.append(str(match_info.get("JIF_Quartile", "N/A")))
                cas_quartile_list.append(str(match_info.get("CAS_Quartile", "N/A")))
            else:
                jif_list.append("N/A")
                jif_quartile_list.append("N/A")
                cas_quartile_list.append("N/A")

        query_df["IF"] = jif_list
        query_df["JCR_Quartile"] = jif_quartile_list
        query_df["CSA_Quartile"] = cas_quartile_list
        query_df = query_df.fillna("N/A")
        query_df.to_csv(csv_path, index=False)


def build_search_info(
    search_keywords: str,
    paper_type: str,
    release_date_cutoff: int | None,
    grab_total: int | None,
    save_path: str,
) -> dict[str, str]:
    return {
        "search_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "search_keywords": search_keywords,
        "paper_type": paper_type,
        "release_date_cutoff": release_date_cutoff,
        "grab_total": grab_total,
        "save_path": save_path,
    }
