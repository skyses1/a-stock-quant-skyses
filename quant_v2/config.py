"""
全局配置文件 (config.py)
统一管理环境变量、路径、代理等，消除硬编码 (Audit Fix #8)
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件 (如果存在)
load_dotenv()

# 1. 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("QUANT_DB_PATH", os.path.join(BASE_DIR, "quant_system.db"))

# 2. 网络代理配置 (默认使用环境变量，若无则留空)
HTTP_PROXY = os.getenv("HTTP_PROXY", "http://5.5name.cn:10831")

# 3. 交易成本配置 (Audit Fix #6)
TRADING_FEES = {
    "commission_rate": 0.00025,  # 佣金：万分之 2.5
    "stamp_tax_rate": 0.001,     # 印花税：千分之 1 (卖出收)
    "slippage_rate": 0.001       # 滑点：千分之 1
}

# 4. 进化引擎配置
EVOLUTION_CONFIG = {
    "min_sample_size": 30,       # 最小样本数门槛 (建议 60+)
    "min_return_threshold": 0.03 # 最小收益提升门槛 (3%)
}
