---
name: pubmed-research-assistant
description: Plan and execute PubMed literature discovery from an initial research idea through final reading outputs. Use when the user is still shaping a topic, needs help turning a vague biological or medical question into searchable PubMed queries, wants interactive query refinement and filter confirmation, or wants to run a local PubMed retrieval, ranking, and HTML reading-list workflow from either a final query string or an existing PubMed Excel export.
---

# PubMed Research Assistant

Drive the workflow from research intent to readable outputs. Do not assume the user already has a downloaded PubMed table.

## Prerequisites

Before starting, ensure you have set up your NCBI API key for faster and more reliable PubMed queries:

1. Obtain an NCBI API key from https://www.ncbi.nlm.nih.gov/account/settings/
2. Set it as an environment variable:
   - On Windows: `set NCBI_API_KEY=your_key_here`
   - On Linux/Mac: `export NCBI_API_KEY=your_key_here`
   - Or use `PUBMED_API_KEY` as an alternative name

If no API key is provided, the tool will work but may be subject to rate limits.

## Start From The Research Question
1. Convert the user's rough idea into a one-sentence research objective.
2. If the topic is still vague, offer a compact ideation frame:
- biological process or disease context
- target genes, pathways, cell types, or interventions
- mechanism, biomarker, method, or translational angle
- species, tissue, model, or assay constraints
3. Propose 2 or 3 PubMed query candidates:
- one strict and precise
- one broader recall-oriented
- one optional mechanism-focused version if useful
4. Explain the tradeoff of each query in one sentence.
5. Ask the user to confirm or edit the final query before execution.

## Confirm Execution Settings
Confirm these items in one compact block before running anything:
1. Topic label for filenames
2. Final PubMed query string
3. Output directory (default: abstract/)
4. File naming prefix (derived from topic if not specified)
5. Time scope
6. Publication type
7. IF or quartile constraints if the user wants them
8. JCR/CSA table path (optional, for IF and quartile annotation)
9. Ranking mode and top-N cap

If the user has no preference, use these defaults:
- output directory: `abstract/`
- publication type: `Journal Article`
- ranking: `hybrid`
- weights: date `0.4`, IF `0.3`, keyword `0.3`
- top-N: `150`

## Execution Paths
Choose one path explicitly.

### Path A: Start From Topic Or Final Query
Use the pipeline script when the user wants the full workflow without first producing a local xlsx.

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_topic_pipeline.py `
  --topic "mitophagy crosstalk in septic cardiomyopathy" `
  --query "(mitophagy[Title/Abstract] OR mitochondrial autophagy[Title/Abstract]) AND (septic cardiomyopathy[Title/Abstract] OR sepsis-induced cardiac dysfunction[Title/Abstract])" `
  --keywords "mitophagy,septic cardiomyopathy,cardiac dysfunction" `
  --output-dir "abstract/mitophagy_sepsis" `
  --years-back 10 `
  --paper-type "Journal Article" `
  --max-csa-quartile 1 `
  --min-if 10 `
  --jcr-path "path/to/JCR_CSA_2025.xlsx" `
  --sort-by hybrid
```

If JCR path is not provided, IF/quartile annotation will be skipped.

### Path B: Start From An Existing PubMed Excel File
Use the post-process script when the retrieval step already exists and only filtering, ranking, or HTML export is needed.

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_postprocess.py `
  --input "abstract\example.xlsx" `
  --keywords "mitophagy,sepsis,cardiomyocyte" `
  --output-dir "abstract/mitophagy_sepsis_processed" `
  --years-back 10 `
  --max-csa-quartile 1 `
  --min-if 10 `
  --sort-by hybrid
```

If the input file does not exist, the script will fail with a clear error message.

## Output Rules
Always report exact output paths for:
- raw fetched xlsx when Path A is used
- ranked xlsx
- HTML reading list

Prefer saving into `abstract/` unless the user specifies otherwise.

## Good Prompt Starters
Offer or accept prompts like these:
- `Use $pubmed-research-assistant to turn my idea into two PubMed search strategies.`
- `Use $pubmed-research-assistant to narrow this topic and then run the full pipeline.`
- `Use $pubmed-research-assistant to re-rank my existing PubMed xlsx by keyword and date.`

## Failure Handling
- If API key is not set, inform the user and suggest setting NCBI_API_KEY.
- If IF or quartile data is unavailable (no JCR path provided), continue without those filters and say so explicitly.
- If the query is too broad, suggest one narrower revision before running again.
- If the result count is too small, broaden synonyms or relax one filter at a time.
- If input file does not exist in Path B, provide the exact path checked and ask user to verify.
