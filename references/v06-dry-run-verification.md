# v0.6-beta Dry-Run 验证流程

## 背景
东方财富 `push2.eastmoney.com` `clist` 端点从沙箱 IP 不可达（RemoteDisconnected），dry-run 使用预设真实板块-个股映射验证链路。

## 验证步骤

### 1. 清理当天旧数据
```python
conn.execute("DELETE FROM daily_stock_recommendations WHERE trade_date = ?", (date,))
conn.execute("DELETE FROM daily_sector_recommendations WHERE trade_date = ?", (date,))
conn.execute("DELETE FROM daily_recommendation_reviews WHERE trade_date = ?", (date,))
conn.commit()
```

### 2. 运行推荐引擎 dry-run
```bash
cd /home/admin/.hermes/scripts/quant_v2 && python3 dry_run.py
```

### 3. 验收检查清单

| 检查项 | 标准 |
|--------|------|
| 板块→个股映射 | 每只股票真实属于对应板块（非全市场 Top） |
| 板块推荐数量 | 1-3 条 |
| 个股推荐数量 | 每板块 3 只 |
| source_timestamp | `T-1 close` |
| data_cutoff_time | `T-1 close` |
| 状态 | 全部 PENDING |
| UNIQUE 约束 | 重复插入被拦截 |
| 无 T 日 close 参与推荐 | ✅ |

### 4. 运行复盘引擎 dry-run
同 `dry_run.py` 自动执行。

### 5. 复盘验收检查清单

| 检查项 | 标准 |
|--------|------|
| PENDING → REVIEWED | 成功 |
| PENDING → REJECTED | 一字涨停/停牌时触发 |
| entry_price = open * 1.002 | ✅ |
| day_return 独立字段 | ✅ |
| excess_vs_benchmark 独立字段 | ✅ |
| excess_vs_sector 独立字段 | ✅ |
| CSV 导出 | `/tmp/review_{date}.csv` |

### 6. 预设真实板块-个股映射
```python
SECTOR_STOCK_MAP = [
    {"sector_code": "BK0494", "sector_name": "半导体",
     "stocks": ["688981 中芯国际", "002371 北方华创", "603501 韦尔股份"]},
    {"sector_code": "BK0473", "sector_name": "新能源",
     "stocks": ["300750 宁德时代", "002594 比亚迪", "300274 阳光电源"]},
    {"sector_code": "BK0455", "sector_name": "证券",
     "stocks": ["601211 国泰君安", "600030 中信证券", "601688 华泰证券"]},
]
```

## 生产环境要求
- 配置 `EASTMONEY_PROXY` 环境变量
- 配置 `TENCENT_PROXY` 环境变量
- 恢复真实 API 调用（`recommendation_engine.py` 的 `fetch_top_sectors` 和 `fetch_stocks_in_sector`）
- 确保代理可达后再恢复 WeCom 推送
