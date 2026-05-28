# A 股量化实战系统 v2.0：架构设计与自我进化逻辑

> **文档用途**：本文档旨在向第三方审计者（其他 AI 模型或人类专家）阐述本系统的核心逻辑、数据流向、风控机制以及自我进化闭环，以评估其设计合理性与潜在风险。

---

## 1. 系统概述 (Executive Summary)

**项目名称**：A-Stock Quant System (v2.0)
**核心理念**：**"宏观映射微观，数据驱动决策，系统自我进化"**。
**目标**：构建一个能够利用预测市场（Polymarket）概率变化预判 A 股板块轮动，并结合 A 股微观资金流向进行量化打分，最终实现策略参数自动优化的 AI Agent 交易系统。

### 🎯 解决的痛点
传统量化系统往往是“静态”的——策略写好后参数不变，直到市场环境改变导致策略失效。
本系统引入了 **Evolution Engine (进化引擎)**，能够定期回溯历史表现，自动调整风控参数（如 ATR 止损系数），实现“代码级的自我进化”。

---

## 2. 系统架构 (System Architecture)

系统采用轻量级微服务架构，专为 Hermes Agent 的沙箱/云端环境设计（无重型依赖如 PyTorch/AKShare）。

### 2.1 模块拓扑

```mermaid
graph TD
    User[用户 / 终端] --> Agent[Hermes Agent]
    
    subgraph Data_Layer [数据层 (无状态)]
        API_PM[Polymarket API (宏观)]
        API_TX[Tencent API (实时行情)]
        API_EM[Eastmoney API (资金流)]
    end
    
    subgraph Core_Logic [核心逻辑层]
        Scoring[📊 四维打分卡]
        Risk[⚖️ 动态风控引擎]
        DB[(💾 SQLite 数据库)]
    end
    
    subgraph Evolution [🧬 进化引擎层]
        Backtest[回溯测试模拟器]
        Optimizer[参数寻优算法]
        Patcher[🔧 源代码自动修补]
    end
    
    Agent --> API_TX
    Agent --> API_EM
    Agent --> API_PM
    
    API_TX --> Scoring
    API_EM --> Scoring
    API_PM --> Scoring
    
    Scoring --> Risk
    Risk --> DB
    DB --> Backtest
    
    Backtest --> Optimizer
    Optimizer --> Patcher
    Patcher --> Risk
```

---

## 3. 核心算法逻辑 (Core Algorithms)

### 3.1 四维打分模型 (4D Scoring Model)
系统不使用单一的“看涨/看跌”预测，而是通过加权打分评估当前市场的综合“健康度”。

**公式：** `Total Score = 资金面(40%) + 情绪面(30%) + 宏观面(20%) + 技术面(10%)`

| 维度 | 权重 | 输入指标 | 评分逻辑 |
| :--- | :--- | :--- | :--- |
| **资金面** | **40%** | 两市成交额、北向资金净买入 | 成交>1万亿加分；北向大幅流入加分。 |
| **情绪面** | **30%** | 涨跌幅分布、涨跌停家数 | 指数红盘加分；跌停潮大幅扣分。 |
| **宏观面** | **20%** | Polymarket 风险指数 | 战争/加息概率低 → 风险低 → 高分。 |
| **技术面** | **10%** | 指数相对均线位置 | 多头排列加分；空头排列扣分。 |

**输出：** 0-100 分的系统评分，直接决定建议仓位（如：>80 分建议重仓）。

### 3.2 动态 ATR 止损 (Dynamic ATR Stop Loss)
摒弃“固定 5% 止损”的散户思维，引入机构级的波动率自适应止损。

**逻辑：**
止损位 = `当前价 - (Multiplier × 振幅)`

*   **Multiplier (乘数)**：核心参数，默认为 **2.0**（即 2 倍波动幅度）。
*   **高波动股**（振幅大）：止损距离自动拉宽，防止被洗盘震出。
*   **低波动股**（振幅小）：止损距离收紧，保护本金。

### 3.3 跨市场映射 (Cross-Market Mapping)
*   **输入**：Polymarket 异动事件（如："War Probability 上升至 60%"）。
*   **映射**：硬编码逻辑 `{"Geopolitics": ["Gold", "Oil", "Defense"]}`。
*   **进化**：未来计划通过 `learning_engine.py` 动态调整映射权重。

---

## 4. 自我进化机制 (The Evolution Engine) 🧬

这是本系统的核心创新点。系统如何“自我进化”？

### 4.1 进化循环 (The Loop)
1.  **数据积累**：每天的推荐结果和实际表现存入 `SQLite` (Paper Trading)。
2.  **触发进化**：每周六凌晨，`evolution_engine.py` 自动运行。
3.  **回测模拟**：引擎读取历史数据（目前使用 Mock Data，未来接入真实历史），模拟不同 `Multiplier` 下的策略表现。
4.  **参数寻优**：对比各参数组的最终收益，找出最优解。
5.  **自动修补 (Self-Patching)**：
    *   如果发现新参数（如 4.0）优于旧参数（2.0）；
    *   引擎会**直接修改 `scoring_risk.py` 源代码中的常量**；
    *   自动提交 Git 更新。
6.  **生效**：下周一的早报直接应用新代码。

### 4.2 代码示例 (Self-Patching Logic)
```python
def update_source_code(file_path, old_mult, new_mult):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 精准替换 multiplier 参数
    if f"multiplier={old_mult}" in content:
        new_content = content.replace(f"multiplier={old_mult}", f"multiplier={new_mult}")
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ 代码已自我修改，新策略生效。")
```

---

## 5. 当前局限性与未来规划 (Limitations & Roadmap)

### 5.1 已知局限
1.  **数据源延迟**：使用的是 HTTP API，非 Level-2 Tick 数据，存在秒级延迟。
2.  **Mock Data 依赖**：目前的进化引擎基于模拟数据（Mock Data）运行，尚未积累足够的真实实盘数据（Paper Trading 刚刚开始）。
3.  **线性映射**：跨市场映射目前是基于规则（Rule-based），尚未引入机器学习模型进行非线性拟合。
4.  **沙箱限制**：无法安装重型库（如 PyTorch），无法运行复杂的深度学习回测。

### 5.2 路线图
*   **Phase 1 (Current)**: 跑通“数据采集 -> 策略生成 -> 记录 -> 进化”的最小闭环。
*   **Phase 2 (Next Month)**: 积累 30 天真实数据后，替换 Mock Data，进行首次真实进化。
*   **Phase 3 (VPS 部署)**: 迁移至 VPS，引入 AKShare/PyTorch，实现基于机器学习的因子挖掘。

---

## 6. 待审计问题 (Questions for Review)

请作为高级量化架构师或 AI 专家，对以下问题给出评估：

1.  **安全性评估**：系统具备**“自动修改自身源代码”**的能力。这种 Self-Patching 行为在量化系统中是否安全？是否存在陷入死循环（如参数在 2.0 和 4.0 之间反复跳跃）的风险？如何设计“参数锁”来防止退化？
2.  **数据有效性**：在没有 Level-2 数据的情况下，仅凭日线 Close/High/Low 和 15 分钟延迟资金流，是否足以支撑量化决策？“腾讯行情 API"的并发限制是否会导致盘中数据缺失？
3.  **进化频率**：目前设定为“每周进化一次”。在 A 股这种轮动极快的市场，一周的频率是否太慢？还是说太频繁会导致过拟合（Overfitting）？
4.  **止损逻辑**：动态 ATR 止损中，使用 `Daily Range` 作为 ATR 的代理指标是否合理？是否应该引入过去 N 日的平均波动率（如 `TA-Lib` 中的 ATR）？
5.  **跨市场关联**：Polymarket 的概率（通常以美元流动性计价）映射到 A 股（人民币资产）时，是否存在显著的滞后性或失真？是否需要引入汇率因子？

---

**文档版本**：v2.0.1
**生成日期**：2026-05-28
**维护者**：Hermes Agent (Skyses1)
