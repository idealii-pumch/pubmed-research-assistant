# 参考文献格式规范

项目内所有参考文献统一采用以下格式。

## 标准格式

```
N. AuthorA, AuthorB, AuthorC. Title of the article. *Journal Abbreviation* Year; **Volume**(Issue):Pages. [PMID: XXXXXXXX](https://pubmed.ncbi.nlm.nih.gov/XXXXXXXX/)
```

### 要素

| 要素 | 要求 | 示例 |
|------|------|------|
| 序号 | 数字 + 英文句点 + 空格 | `1. ` |
| 作者 | 姓氏首字母 + 空格 + 名缩写(大写+句点)，逗号分隔，最后一位前用逗号 | `Hu J, Stiehl DP, Setzer C, et al.` |
| 标题 | 首字母大写，专有名词大写，结尾句点 | `Interaction of HIF and USF signaling pathways...` |
| 期刊名 | *斜体*，标准缩写 | *Mol Cancer Res* |
| 年份 | 后加分号 | 2011; |
| 卷号 | **粗体**，后跟括号 | **9**(11) |
| 页码 | 冒号分隔起止 | :1520–1536 |
| PMID | 带超链接，格式固定 | `[PMID: 21984181](https://pubmed.ncbi.nlm.nih.gov/21984181/)` |
| 说明 | 中文破折号 + 一句话注释（可选） | `— BNIP3 HRE/E-box 重叠` |

### 完整示例

```
1. Bruick RK. Expression of the gene encoding the proapoptotic Nip3 protein is induced by hypoxia. *PNAS* 2000; **97**(16):9082–9087. [PMID: 10922063](https://pubmed.ncbi.nlm.nih.gov/10922063/) — BNIP3 promoter HRE 鉴定
2. Sowter HM, Ratcliffe PJ, Watson P, Greenberg AH, Harris AL. HIF-1-dependent regulation of hypoxic induction of the cell death factors BNIP3 and NIX in human tumors. *Cancer Res* 2001; **61**(18):6669–6673. [PMID: 11559532](https://pubmed.ncbi.nlm.nih.gov/11559532/) — HIF-1 依赖性 BNIP3 调控
3. Hu J, Stiehl DP, Setzer C, Wichmann D, Shinde DA, Rehrauer H, et al. Interaction of HIF and USF signaling pathways in human genes flanked by hypoxia-response elements and E-box palindromes. *Mol Cancer Res* 2011; **9**(11):1520–1536. [PMID: 21984181](https://pubmed.ncbi.nlm.nih.gov/21984181/) — BNIP3 HRE/E-box 重叠，HIF/USF 竞争
4. Liu X, Zhang W, Wu Z, Yang Y, Kang YJ. Copper levels affect targeting of hypoxia-inducible factor 1α to the promoters of hypoxia-regulated genes. *J Biol Chem* 2018; **293**(38):14669–14677. [PMID: 30082314](https://pubmed.ncbi.nlm.nih.gov/30082314/) — BNIP3 功能 HRE 突变验证
5. Tracy K, Dibling BC, Spike BT, Knabb JR, Schumacker P, Macleod KF. BNIP3 is an RB/E2F target gene required for hypoxia-induced autophagy. *Mol Cell Biol* 2007; **27**(17):6229–6242. [PMID: 17576813](https://pubmed.ncbi.nlm.nih.gov/17576813/) — BNIP3 启动子 RB/E2F 调控
```

## 特殊情况

### 多位作者（>6 位）
列出前 6 位，后加 `, et al.`

### 无说明注释
可省略最后的破折号和注释。至少保留 PMID 和链接。

### 期刊名缩写规则
遵循 NLM (National Library of Medicine) 标准缩写。不确定时使用全称。

## 引用在正文中的标注

- 用 `[PMID: XXXXXXXX](链接)` 格式标注，便于直接跳转 PubMed
- 不要在正文中使用纯数字上标 `[1]` 这类格式，除非同时附有独立的参考文献列表

## 自动检索优先顺序

撰写参考文献时，按以下顺序确认信息：
1. PubMed (https://pubmed.ncbi.nlm.nih.gov/) — 最权威，PMID 唯一
2. 论文 DOI 页面 — 补充期刊格式细节
3. 期刊官网 — 确认缩写和卷期页码
