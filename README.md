# A 股量化实战系统 (A-Stock Quant)

一套全天候自动化交易参谋系统，专为 A 股市场设计。融合了 Polymarket 宏观概率预测与 A 股微观资金数据分析，具备**自我验证、策略自适应、盘中实时监控**能力。

## 🚀 核心功能

| 模块 | 时间 | 功能描述 |
| :--- | :--- | :--- |
| **📅 深度实战报告** | 08:00 | 宏观映射、资金情绪分析、观察池推荐、**昨日策略评分验证**。 |
| **🔔 盘中雷达 (早)** | 10:00 | 早盘量能确认，判断是“诱多”还是“真强”，给出买卖点提示。 |
| **🔔 盘中雷达 (晚)** | 14:30 | 尾盘风险诊断，决定是“持股过夜”还是“减仓避险”。 |
| **🧠 策略自适应** | 自动 | 根据昨日评分自动调整今日权重。**高分板块加仓，低分板块降级。** |

## 🧩 系统亮点

*   **跨市场映射**: 将全球宏观事件（如降息预期、地缘冲突）映射为具体的 A 股板块机会。
*   **原生数据抓取**: 不依赖第三方重型库（如 AKShare），使用轻量级 Python 脚本直连东方财富底层接口，极速稳定。
*   **闭环进化**: 每日自动复盘昨日推荐表现，计算得分（涨停=100 分），让策略“吃一堑长一智”。

## 🛠️ 安装与部署

### 1. 适用于 Hermes Agent
直接克隆本仓库到 skills 目录：
```bash
cd ~/.hermes/skills/devops
git clone https://github.com/skyses1/skyses.git a-stock-quant
```

### 2. 定时任务配置 (Cron Jobs)
在 Hermes Agent 中创建以下三个 Cron Job：

**Job 1: 早报 (08:00)**
*   **Prompt**: 参考 `references/cron-prompts.md` 中的"08:00 深度实战报告"。
*   **Context**: 需继承昨日报告 ID，用于策略自适应。

**Job 2: 盘中雷达 (10:00)**
*   **Prompt**: 参考 `references/cron-prompts.md` 中的"10:00 盘中雷达"。
*   **Context**: 读取早报观察池代码。

**Job 3: 尾盘雷达 (14:30)**
*   **Prompt**: 参考 `references/cron-prompts.md` 中的"14:30 尾盘雷达"。
*   **Context**: 读取早报观察池代码。

### 3. 环境要求
*   **网络**: 需配置代理以访问 Polymarket API (参考 `hermes config set HTTP_PROXY ...`)。
*   **技能**: 需加载 `web-search` 和 `polymarket` 技能。

## 📂 文件结构
```text
a-stock-quant/
├── SKILL.md                # 技能核心描述
├── README.md               # 本说明文档
├── references/
│   ├── implementation.md   # 技术架构与实现原理
│   └── cron-prompts.md     # 定时任务 Prompt 集合
└── scripts/
    └── fetch_data.py       # A 股数据原生抓取脚本 (东方财富接口)
```

## ⚠️ 免责声明
本系统生成的报告及推荐标的仅供**参考和研究**，不构成任何直接的投资建议。市场有风险，交易需谨慎。AI 无法完全预测突发事件，请务必结合实际情况操作。

---
**Made with ❤️ by Hermes Agent & skyses1**