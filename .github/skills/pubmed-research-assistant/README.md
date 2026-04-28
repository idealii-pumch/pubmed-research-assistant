# PubMed Research Assistant (Standalone)

A self-contained workflow for PubMed search, CSV export, filtering, ranking, and HTML reading list output.

## Prerequisites

- Python 3.8+
- pandas: `pip install pandas`
- Optional: NCBI API key for higher rate limits
  - Windows: `set NCBI_API_KEY=your_key_here`
  - Linux/Mac: `export NCBI_API_KEY=your_key_here`
  - Or use `PUBMED_API_KEY`

## Quick Start (from this folder)

```powershell
# From repo root
cd .github\skills\pubmed-research-assistant

python scripts\pubmed_topic_pipeline.py `
  --topic "mitophagy in septic cardiomyopathy" `
  --query "(mitophagy[Title/Abstract] OR mitochondrial autophagy[Title/Abstract]) AND (septic cardiomyopathy[Title/Abstract] OR sepsis-induced cardiac dysfunction[Title/Abstract])" `
  --keywords "mitophagy,septic cardiomyopathy,cardiac dysfunction" `
  --output-dir "abstract" `
  --run-dir-name "mitophagy_sepsis" `
  --years-back 10 `
  --paper-type "Journal Article" `
  --max-csa-quartile 1 `
  --min-if 10 `
  --jcr-path "references\JCR_CSA_2025.csv" `
  --sort-by hybrid
```

Outputs:
- raw csv
- ranked csv
- html reading list
- query log txt

## Post-process an existing CSV

```powershell
python scripts\pubmed_postprocess.py `
  --input "abstract\example.csv" `
  --keywords "mitophagy,sepsis,cardiomyocyte" `
  --output-dir "abstract\mitophagy_sepsis_processed" `
  --years-back 10 `
  --max-csa-quartile 1 `
  --min-if 10 `
  --sort-by hybrid
```

## Files

- scripts/pubmed_topic_pipeline.py
- scripts/pubmed_postprocess.py
- scripts/pubmed_fetch_utils.py
- references/JCR_CSA_2025.csv
