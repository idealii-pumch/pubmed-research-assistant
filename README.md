# 📚 PubMed Research Assistant

> 一个强大的 PubMed 文献检索与阅读列表生成工具，支持从研究想法到可读 HTML 输出的完整工作流。

这个 skill 现在支持对话和命令行两种模式，她帮助你：

1. 🔍 从一个宽泛的研究想法开始，先帮你收敛主题并生成 PubMed 检索式。
2. 📥 帮你下载 PubMed 文章的 PMID、杂志名称、发表日期、标题、摘要和关键词，并提供 DOI、影响因子以及分区，形成一个汇总 `xlsx`。
3. 🎯 根据你的需求，做筛选和排序，并生成带有侧边导航栏、已读和星标功能、可切换主题的舒适的 `HTML` 阅读列表。
4. 💾 你可在本地编辑和保存这些文件，让它们成为你的个人研究资料。

## 🚀 安装后怎么调用

如果 skill 已被安装并能被 Codex 发现，最直接的说法就是：

- `用 pubmed-research-assistant 帮我把这个课题想法收敛几个 PubMed 检索式。`
- `用 pubmed-research-assistant 从主题构思开始，确认后直接跑完整检索流程。`
- `用 pubmed-research-assistant 处理我现有的 xlsx，导出 html 阅读列表。`

## ⚠️ 重要前提：设置 NCBI API Key

为了避免 PubMed 查询的速率限制并获得更好的性能，请先设置你的 NCBI API Key：

1. 🌐 访问 [NCBI Account Settings](https://www.ncbi.nlm.nih.gov/account/settings/) 获取 API Key。
2. 🔧 设置环境变量：
   - **Windows**: `set NCBI_API_KEY=your_actual_key`
   - **Linux/Mac**: `export NCBI_API_KEY=your_actual_key`
   - 或者使用 `PUBMED_API_KEY` 作为替代名称。

> 💡 **提示**: 如果不设置，工具仍能工作，但可能较慢且有速率限制。

---

## 💬 1. 通过对话开始研究

### 📝 场景 1：从研究主题开始

可以直接说：

```text
我想研究脓毒症心肌病里的线粒体自噬机制，先帮我拆成两个 PubMed 检索策略，一个严格，一个宽松。
```

然后继续补充：

```text
用严格版，近 10 年，Journal Article，优先 1 区和 IF>=10，最后按关键词命中和时间综合排序。
```

### 📊 场景 2：我已经有 PubMed 导出的 xlsx

```text
用 pubmed-research-assistant 处理 abstract/example.xlsx，关键词用 mitophagy,sepsis,cardiomyocyte，近 10 年，导出 html。
```

---

## 🖥️ 2. 通过命令行开始研究

### 🔄 1. 从最终检索式直接抓取并产出阅读清单

如果你更喜欢命令行模式，也可以直接用以下语句从头得到你想要的内容

```powershell
.\.venv\Scripts\python.exe .github/skills/pubmed-research-assistant/scripts/pubmed_topic_pipeline.py `
  --topic "mitophagy in septic cardiomyopathy" `
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

**输出包括：**

- 📄 原始抓取结果 `raw xlsx`
- 📈 筛选、排序后的 `*_ranked.xlsx`
- 🌐 可阅读的 `*_reading_list.html`

**说明：**

- 🔑 如果环境变量里有 `NCBI_API_KEY` 或 `PUBMED_API_KEY`，脚本会自动读取。
- 📊 如果没有提供 `--jcr-path`，IF/分区注释会被跳过。
- 📁 输出目录默认为 `abstract/`，文件名基于 `--topic` 或查询自动生成。

### 🔧 2. 对已有 xlsx 做后处理

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

> ⚠️ **注意**: 如果输入文件不存在，脚本会报错并显示检查的路径。

---

## 📂 文件保存位置和命名

| 项目 | 说明 |
|------|------|
| **默认输出目录** | `abstract/` （相对于项目根目录） |
| **文件名命名** | 基于 `--topic` 参数自动生成安全的文件名。如果未提供 topic，则从查询字符串派生。 |
| **自定义** | 使用 `--output-dir` 指定输出目录。文件名会自动添加时间戳以避免冲突。 |

---

## 📊 JCR 分区表

JCR/CSA 分区表用于添加影响因子和分区信息：

- 🔄 默认情况下，如果未提供 `--jcr-path`，IF/分区注释会被跳过。
- 📁 你可以提供自己的 JCR 表路径：`--jcr-path "path/to/your/JCR_CSA.xlsx"`
- 🌍 该表可以公开分享，因为它不包含个人敏感信息。

---

## 🛠️ 故障排除

- **🔑 API Key 未设置**：如果未设置 NCBI_API_KEY，查询可能被限速。建议设置环境变量。
- **📊 IF/分区数据不可用**：如果没有 JCR 表，脚本会继续但跳过 IF 过滤。
- **🔍 查询太宽泛**：如果结果太多，建议缩小查询范围。
- **📉 结果太少**：放宽同义词或放松一个过滤条件。
- **❌ 输入文件不存在**：检查路径是否正确，脚本会显示检查的完整路径。

---

## 📁 目录结构

```text
pubmed-research-assistant/
├─ 🤖 agents/
│  └─ openai.yaml
├─ 📖 README.md
├─ 📋 SKILL.md
└─ 🐍 scripts/
   ├─ pubmed_postprocess.py
   └─ pubmed_topic_pipeline.py
```
