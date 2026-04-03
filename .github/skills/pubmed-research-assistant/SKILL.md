---
name: pubmed-research-assistant
description: Use when the user wants end-to-end PubMed literature retrieval and review from a topic idea, including iterative query refinement, interactive filter confirmation (publication time, quartile, impact factor), custom ranking (date/IF/keyword hit frequency), HTML abstract export.
---

## Runbook
1. Clarify topic and objective in one sentence.
2. Propose 2 to 3 candidate PubMed query strings using Boolean logic, synonyms, and field tags.
3. Ask user to confirm or modify query strategy; iterate until final query is approved.
4. Confirm filters interactively:
- publication time range (`years_back` or explicit start/end date)
- `CSA_Quartile` threshold
- impact factor threshold
- article type constraints if needed
5. Execute existing PubMed pipeline first (reuse local tool/notebook):
- `tools/Pubmed_qeury.ipynb`
- produce `.xlsx` with columns like `Title`, `Abstract`, `publish_date`, `IF`, `CSA_Quartile`
6. Run post-process script to filter, rank, and export HTML reading list.

## Query Strategy Rules
- Expand core concept with synonyms, abbreviations, and mechanism/outcome terms.
- Prefer explicit field tags for precision when useful:
- `"[Title/Abstract]"`, `"[MeSH Terms]"`, `"[Publication Type]"`, `"[Date - Publication]"`
- Keep one strict query and one broad query for iteration.
- Show user the exact final query before running retrieval.

## Filter Confirmation Template
Use this exact structure when asking for confirmation:
1. Topic and scope
2. Final query string
3. Time filter
4. Quartile/IF filter
5. Result cap and sorting mode

## Ranking and Export
Run:

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_postprocess.py `
  --input "abstract\xxx.xlsx" `
  --keywords "keyword1,keyword2" `
  --years-back 5 `
  --max-csa-quartile 1 `
  --min-if 10 `
  --sort-by hybrid `
  --w-date 0.4 --w-if 0.3 --w-keyword 0.3
```

Sort modes:
- `date`: publish date
- `if`: impact factor
- `keyword`: search-term hit frequency in title+abstract
- `hybrid`: weighted composite of date + IF + keyword hit

## Outputs
The script generates:
- filtered ranked table: `*_ranked.xlsx`
- HTML abstract reading list: `*_reading_list.html`

Always save outputs locally and report exact paths.
