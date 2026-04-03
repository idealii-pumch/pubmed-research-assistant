# PubMed Research Assistant

这个 skill 现在支持两种起点：

1. 从一个模糊研究想法开始，先帮你收敛主题并生成 PubMed 检索式。
2. 从已有的 PubMed `xlsx` 开始，只做筛选、排序和 HTML 阅读清单导出。

它不再要求你必须先准备好本地下载结果。

## 安装后怎么调用

如果 skill 已被安装并能被 Codex 发现，最直接的说法就是：

- `Use $pubmed-research-assistant to turn my topic into two PubMed queries.`
- `Use $pubmed-research-assistant to refine this idea and run the full PubMed pipeline.`
- `Use $pubmed-research-assistant to rank my existing PubMed xlsx by keyword and date.`

也可以直接用中文：

- `用 pubmed-research-assistant 帮我把这个课题想法收敛成两个 PubMed 检索式。`
- `用 pubmed-research-assistant 从主题构思开始，确认后直接跑完整检索流程。`
- `用 pubmed-research-assistant 处理我现有的 xlsx，导出 html 阅读列表。`

## 推荐对话流程

### 场景 1：从研究主题开始

可以直接说：

```text
我想研究脓毒症心肌病里的线粒体自噬机制，先帮我拆成两个 PubMed 检索策略，一个严格，一个宽松。
```

然后继续补充：

```text
用严格版，近 10 年，Journal Article，优先 1 区和 IF>=10，最后按关键词命中和时间综合排序。
```

### 场景 2：我已经有 PubMed 导出的 xlsx

```text
用 pubmed-research-assistant 处理 abstract/example.xlsx，关键词用 mitophagy,sepsis,cardiomyocyte，近 10 年，导出 html。
```

## 现在有哪些脚本

### 1. 从最终检索式直接抓取并产出阅读清单

这个脚本把原来 notebook 里的抓取逻辑抽出来了，安装 skill 后更容易直接调用。

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_topic_pipeline.py `
  --topic "mitophagy in septic cardiomyopathy" `
  --query "(mitophagy[Title/Abstract] OR mitochondrial autophagy[Title/Abstract]) AND (septic cardiomyopathy[Title/Abstract] OR sepsis-induced cardiac dysfunction[Title/Abstract])" `
  --keywords "mitophagy,septic cardiomyopathy,cardiac dysfunction" `
  --years-back 10 `
  --paper-type "Journal Article" `
  --max-csa-quartile 1 `
  --min-if 10 `
  --sort-by hybrid
```

输出包括：

- 原始抓取结果 `raw xlsx`
- 排序后的 `*_ranked.xlsx`
- 可阅读的 `*_reading_list.html`

说明：

- 如果环境变量里有 `NCBI_API_KEY` 或 `PUBMED_API_KEY`，脚本会自动读取。
- 如果本机没有 `E:\Python\GrabPubmed\JCR_CSA_2025.xlsx`，可以手动传 `--jcr-path`。
- 没有 JCR 表时，脚本会跳过 IF/分区注释，而不是直接失败。

### 2. 对已有 xlsx 做后处理

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_postprocess.py `
  --input "abstract\example.xlsx" `
  --keywords "mitophagy,sepsis,cardiomyocyte" `
  --years-back 10 `
  --max-csa-quartile 1 `
  --min-if 10 `
  --sort-by hybrid
```

## 改进点

- 把“必须先有本地 xlsx”改成“可以从研究问题开始”。
- 把 notebook 里的检索步骤变成了可执行脚本。
- 让 `pubmed_postprocess.py` 同时支持命令行和被其他脚本复用。
- 给 skill 增加了更明确的触发语和调用入口。
- 对缺少 JCR/CSA 文件的环境做了更温和的降级处理。

## 目录

```text
pubmed-research-assistant/
├─ agents/
│  └─ openai.yaml
├─ README.md
├─ SKILL.md
└─ scripts/
   ├─ pubmed_postprocess.py
   └─ pubmed_topic_pipeline.py
```
