# Restaurant Analyzer — Claude Code 项目说明

## 项目简介
餐厅菜单智能分析系统，四阶段流水线：
菜单工程（波士顿矩阵）→ 情感分析 → 竞品比对 → AI报告生成 + HTML输出

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key（可选，无 Key 也能运行 mock 模式）
cp .env.example .env        # 然后填入 ANTHROPIC_API_KEY

# 运行完整流程
python -X utf8 main.py all

# 启动 Web 服务
uvicorn app:app --reload --port 8000
# 浏览器打开 http://localhost:8000
```

## 目录结构

```
restaurant-analyzer/
├── main.py                         # 全流程入口（Phase 1-4）
├── app.py                          # FastAPI 后端（/upload /analyze /report /history）
├── frontend/index.html             # 纯 HTML 前端
├── config/settings.py              # 路径、API Key、USE_MOCK_API 开关
├── config/keywords.py              # 暂未在此项目使用
├── sample_data/
│   ├── menu_sample.csv             # 20道菜示例（中文，含price/cost/monthly_orders/rating）
│   ├── reviews_sample.csv          # 51条顾客评价
│   └── competitor_sample.csv       # 3家竞品 × 10道菜
├── src/
│   ├── ingestion/data_loader.py    # CSV 读取 + 校验 + 清洗
│   ├── analysis/
│   │   ├── menu_engineering.py     # 波士顿矩阵分类
│   │   ├── sentiment_analyzer.py   # 情感分析（Claude API / mock）
│   │   └── competitor_analysis.py  # 竞品定价对比
│   ├── output/
│   │   ├── report_generator.py     # AI 报告/建议/文案（Claude API / mock）
│   │   └── html_report.py          # Jinja2 渲染 final_report.html
│   └── db/history.py               # SQLite 分析历史记录
├── templates/report_template.html  # 报告 Jinja2 模板
└── reports/                        # 输出目录（git 忽略）
```

## Mock vs 真实 API

`config/settings.py` 中 `USE_MOCK_API = not bool(ANTHROPIC_API_KEY)`

- **无 Key**：所有 Claude 调用返回内置 mock 数据，全流程仍可完整运行
- **有 Key**：`sentiment_analyzer.py` + `report_generator.py` 自动切换真实调用（claude-opus-4-8，adaptive thinking，streaming）

## 关键数据格式

菜单 CSV 必须包含列：`dish_name, category, price, cost, monthly_orders, rating`

评价 CSV：`dish_name, review_text`

竞品 CSV：`restaurant_name, dish_name, category, price, rating, monthly_orders`

## 常见任务

| 需求 | 操作 |
|------|------|
| 换一份菜单数据 | 上传到 `sample_data/` 或通过 `POST /upload` |
| 只跑 Phase 1 | `python main.py menu` |
| 只跑情感分析 | `python main.py sentiment` |
| 查看历史记录 | `GET /history` 或 `data/chat_history.db` |
| 修改报告样式 | 编辑 `templates/report_template.html` |

## GitHub
https://github.com/JERICHOxturtle15/restaurant-analyzer
