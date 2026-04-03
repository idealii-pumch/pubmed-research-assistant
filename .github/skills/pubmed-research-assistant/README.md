# PubMed Research Assistant

一个面向文献检索与筛选的轻量级 Skill：  
从主题到检索策略确认，再到筛选、排序和本地 HTML 阅读清单导出。

## 核心能力

- 交互式完善 PubMed 检索式（主题词、同义词、布尔逻辑）
- 可配置筛选条件：发表时间、影响因子、分区
- 多策略排序：`date` / `if` / `keyword` / `hybrid`
- 导出结果：
  - `*_ranked.xlsx`
  - `*_reading_list.html`（支持关键词高亮、书签侧栏、已读/星标、夜间模式）

## 目录结构

```text
pubmed-research-assistant/
├─ SKILL.md
├─ README.md
└─ scripts/
   └─ pubmed_postprocess.py
```

## 快速开始

1. 先通过你现有流程生成 PubMed 原始 `xlsx`（如 `abstract/xxx.xlsx`）。
2. 运行后处理脚本：

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_postprocess.py `
  --input "abstract\xxx.xlsx" `
  --keywords "bnip3,nix,lc3" `
  --years-back 10 `
  --max-csa-quartile 1 `
  --sort-by keyword `
  --top-n 150
```

## 主要参数

- `--input`：输入 `xlsx`
- `--keywords`：逗号分隔关键词（用于命中统计与高亮）
- `--years-back` / `--start-date` / `--end-date`：时间筛选
- `--min-if`：最低影响因子
- `--max-csa-quartile`：最高分区阈值（1 为最优）
- `--sort-by`：排序模式

## 输出位置

- 默认保存到：`abstract/<topic>_<timestamp>/`
- 也可通过 `--output-dir` 指定路径
