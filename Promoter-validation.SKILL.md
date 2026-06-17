# Promoter-validation.SKILL

用于从 ChIP-seq + RNA-seq 整合分析出发，系统验证转录因子对靶基因启动子的转录调控。可复用于任意基因-转录因子组合的验证实验设计。

## 工作流程概览

```
                   ChIP-seq + RNA-seq
                          │
                    Integrate 分析
                    ┌─────┴─────┐
                    │           │
              Step 1:        Step 2:
           ChIP-qPCR      Promoter Reporter
           验证结合        验证功能激活
```

---

## Step 0: 整合分析定位候选靶基因

### 输入数据
- ChIP-seq peak 注释文件（MACs3 bdgdiff peaks, annotated with gene symbols）
- RNA-seq DESeq2 结果（含 log2FC, padj）

### 筛选流程

```
1. 从 RNA-seq 筛选差异表达基因 (abs(log2FC) > cutoff, padj < 0.05)
2. 取交集：ChIP-seq ⌒ RNA-seq
3. 按 log2FC 排序 + peak LLH score 评估可信度
```

### 输出
- 交集基因列表（含 log2FC, padj, peak 坐标, 注释）
- 优先选择：启动子注释 (Promoter ≤1kb) + 高 log2FC + 显著 padj

---

## Step 1: ChIP-qPCR 验证物理结合

### 1.1 获取 ChIP peak 区序列

从 ChIP-seq peak 注释中获取目标基因的 peak 坐标：

```
Genome: hg38/GRCh38
Method: UCSC Genome Browser → View → DNA
        或 UCSC API: genome.ucsc.edu/getData/sequence
        或 Ensembl REST API
```

### 1.2 分析启动子序列

```python
import re

# 寻找 HRE 基序 (适用于 HIF 家族)
# 通用转录因子结合基序 GCGTG / CACGTG / RCGTG 等
hre_motifs = re.finditer('[AG]CGTG', sequence)

# 反向链基因注意事项：
# 若基因在 minus strand，TSS 在 plus strand 坐标中为基因体起点
# HRE 距 TSS 距离 = TSS_genomic - HRE_start (plus strand)
```

### 1.3 ChIP-qPCR 引物设计原则

| 参数 | 要求 |
|------|------|
| 产物大小 | **80–120 bp**（ChIP-qPCR 最佳范围） |
| 覆盖区域 | ChIP peak summit 区域 |
| 靶向基序 | 覆盖转录因子结合基序（HRE, E-box, etc.） |
| 阴性对照 | 距 peak 上游 >1kb 的基因间区或无 motif 区域 |

**引物数量**：每靶基因设计 2–3 对（1 对核心 + 1 对备选 + 1 对阴性对照）

### 1.4 引物验证流程

| 步骤 | 方法 | 通过标准 |
|------|------|---------|
| 特异性 | 普通 PCR + 琼脂糖凝胶 | 单一条带 |
| 特异性 | qPCR 熔解曲线 | 单一峰，无引物二聚体 |
| 效率 | 10 倍稀释标准曲线 (5 梯度) | 扩增效率 90–110%, R² > 0.99 |

### 1.5 高 GC 序列 PCR 策略

GC 含量 >65% 时必须采取以下措施：

| 方法 | 方案 | 备注 |
|------|------|------|
| 添加剂 | 3–5% DMSO 或 1M Betaine | 降低 DNA 熔解温度 |
| GC Enhancer | NEB Q5 High GC Enhancer 或 Takara GC Buffer | 随聚合酶选择 |
| 预变性 | 98°C 3–5 min | 充分解链 GC-rich 模板 |
| 替代 | 7-deaza-dGTP 替代 dGTP | 极端 GC 使用 |

### 1.6 ChIP-qPCR 预期结果

| 对比 | 预期 |
|------|------|
| TF IP vs IgG @ target promoter | ≥3–5 fold enrichment |
| TF IP vs IgG @ NC region | ≈1 fold (无富集) |
| Hypoxia(处理组) vs Normoxia(对照组) TF IP | 处理组显著更高 |

---

## Step 2: 启动子荧光报告系统

### 2.1 选择报告载体

| 载体 | 特点 | 来源 |
|------|------|------|
| **pGL4.10[luc2]** | 无启动子，Firefly luc2，背景低 | Promega E6651 |
| pGL3-Basic | 经典 Firefly luc+ | Promega E1751 |
| pGL4.20[luc2/Puro] | +Puromycin 筛选，可建稳株 | Promega E6751 |

内参：pRL-TK (Promega E2241) 或 pGL4.74[hRluc/TK] (Promega E6921)

### 2.2 启动子片段选择

从靶基因 TSS 上游取适当长度的基因组片段：

| 方案 | 大小 | 适用场景 |
|------|------|---------|
| 短片段 | 300–600 bp | 只覆盖核心启动子 + 已知结合基序簇 |
| 中片段 | 1–2 kb | 覆盖大多数顺式调控元件（**推荐**） |
| 长片段 | 2–3 kb | 包含远端增强子，复杂度增加 |

### 2.3 克隆方向判断

#### 正向链基因
**Fwd (KpnI) 端** = 上游（低坐标），**Rev (XhoI) 端** = TSS 方向（高坐标）

#### 反向链基因
**Fwd (KpnI) 端** = 上游（高坐标），**Rev (XhoI) 端** = TSS 方向（低坐标）

**验证方法**：
```
1. 在 UCSC Genome Browser 确认基因链方向
2. 确认 TSS 在 plus strand 的坐标
3. 确定上下游方向：
   - plus strand 基因：KpnI 端 (低坐标) → XhoI 端 (高坐标) → luc2
   - minus strand 基因：KpnI 端 (高坐标) → XhoI 端 (低坐标) → luc2
4. 验证：TSS 应位于 HRE/结合基序与 luc2 之间
```

### 2.4 扩增引物设计

| 引物 | 酶切位点 | 序列来源 |
|------|---------|---------|
| **Fwd** | KpnI (GGTACC) | plus strand 序列（基因组 5'→3'） |
| **Rev** | XhoI (CTCGAG) | revcomp of plus strand（末尾端序列的反向互补） |

> 酶切位点前加 3–4 bp 保护碱基（常用 GGG 或 CCG）

### 2.5 突变对照

构建结合基序突变体以证明序列特异性：

```python
# 示例：CACGTG → CAAAG (破坏 HIF-1 结合)
模板序列：...GTGTGG CACGTG CGGCGCG...
突变序列：...GTGTGG CAAAG  CGGCGCG...
```

方法选择：
- **重叠延伸 PCR** (Overlap Extension PCR)：两轮 PCR，最经济
- **Q5 Site-Directed Mutagenesis Kit** (NEB E0554)：简便快速
- **Gibson Assembly** (NEB E2611)：多片段同时拼接

### 2.6 实验分组设计模板

| 组 | 条件 | 质粒 | 目的 |
|----|------|------|------|
| 1 | 对照组 | WT-promoter-luc + 内参 | 基线活性 |
| 2 | **处理组** | WT-promoter-luc + 内参 | 条件诱导 |
| 3 | 对照 + **TF-OV** | WT-promoter-luc + 内参 + TF 过表达质粒 | TF 反式激活 |
| 4 | 处理 + **siTF** | WT-promoter-luc + 内参 | TF 依赖性 |
| 5 | 处理 + siNC | WT-promoter-luc + 内参 | si 对照 |
| 6 | 处理组 | **Mut-promoter-luc** + 内参 | 结合基序依赖性 |
| 7 | TF-OV | **Mut-promoter-luc** + 内参 | 结合基序依赖性 |
| 8 | 对照组 | SV40-luc (阳性对照) + 内参 | 系统对照 |
| 9 | 对照组 | Empty-vector (阴性对照) + 内参 | 背景对照 |

### 2.7 转染与检测参数

| 参数 | 建议 |
|------|------|
| 细胞密度 | 96-well, 1–2×10⁴ cells/well |
| 质粒比 | 实验:内参 = 10:1 (Firefly 100 ng + Renilla 10 ng/well) |
| 转染试剂 | Lipofectamine 3000 或 PEI |
| 处理时间 | 转染后 24h → 处理 24h |
| 检测 | Dual-Glo Luciferase Assay (Promega E2920) |
| 重复 | 3 个生物学重复 × 每个 3 个技术复孔 |

### 2.8 预期结果

| 比较 | 预期 |
|------|------|
| 处理组 / 对照组 (WT-luc) | **显著 ↑** (2–5 fold) |
| TF-OV / Control (WT-luc, 基础条件) | **显著 ↑** |
| siTF / siNC (WT-luc, 处理) | **显著 ↓** (>50%) |
| Mut/WT (处理条件) | **显著 ↓** (接近基线) |
| Mut/WT (TF-OV) | **显著 ↓** |

---

## 完整证据链

```
                    TF → Target 直接转录调控
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ChIP-seq/qPCR    Promoter-luc 报告    蛋白水平验证
    (物理结合)        (功能激活)         (WB, 已有)
          │                │                │
    TF IP 富集        处理→Luc↑        TF-KD → 靶蛋白↓
    at 靶启动子        Mut→Luc→
          │                │                │
          └────────────────┼────────────────┘
                           │
                   闭合证据链 ✅
```

---

## 常见问题处理

### 1. 高 GC 含量基因组启动子
- 多数哺乳动物启动子含 CpG 岛，GC 含量可达 70–80%
- ChIP-qPCR 和克隆 PCR 都必须使用 GC Enhancer/DMSO
- 测序时需注意 GC-rich 区域可能出现的测序偏好

### 2. 反向链基因
- UCSC/Ensembl 的坐标基于 plus strand
- 反向链基因的 promoter 在 plus strand 上位于 TSS 的**高坐标方向**
- 报告载体插入方向必须反转（Fwd = 高坐标端）

### 3. 启动子无基础活性
- 可能是缺失了核心启动子元件（TATA box, Inr, DPE）
- 考虑延长片段覆盖更多远端调控区
- 检查转录因子是否在目标细胞中表达

### 4. ChIP-qPCR 无富集
- ChIP 抗体是否经验证（ChIP-grade, 有文献支持）
- 引物是否覆盖 peak summit（峰值）
- 对照区域是否合适（选无 motif 的转录活性区而非完全随机）

---

## 参考文献 (验证方法)

1. Bruick RK (2000) *PNAS* **97**:9082–9087 — BNIP3 promoter HRE 鉴定, HRE1/HRE2 突变
2. Sowter HM et al. (2001) *Cancer Res* **61**:6669–6673 — BNIP3/NIX 的 HIF-1 依赖性调控
3. Tracy K et al. (2007) *Mol Cell Biol* **27**:6229–6242 — BNIP3 promoter RB/E2F 和 HIF 双重调控
4. Carey MF et al. (2009) *Nat Protoc* — ChIP-qPCR 实验步骤
5. Shlyueva D et al. (2014) *Nat Rev Genet* — Enhancer reporter assays

---

## 模板：引物速查表

| 引物名称 | 序列 (5'→3') | 酶切位点 | 坐标 | 用途 |
|---------|-------------|---------|------|------|
| Gene-F | XXXXXXXXXX | KpnI | chr1:XXXXXX | ChIP Fwd |
| Gene-R | XXXXXXXXXX | - | chr1:XXXXXX† | ChIP Rev |
| NC-F | XXXXXXXXXX | - | chr1:XXXXXX | 阴性对照 |
| Clone-F | GGGGGTACCXXXXXXXXXX | KpnI | chr1:XXXXXX | 报告Fwd |
| Clone-R | CCGCTCGAGXXXXXXXXXX | XhoI | chr1:XXXXXX† | 报告Rev |

†Rev 引物基因组位置 = reverse-complement 的结合坐标
