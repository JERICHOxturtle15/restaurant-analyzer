# 项目背景 & 上下文

## 用户身份
**餐饮品牌策划咨询顾问（品牌经理）**，乙方视角，为餐饮品牌客户提供品牌策划、打法建议、产品创意、体验设计等咨询服务。

## 项目功能

### 1. 菜单分析工具（原始功能）
- 上传餐厅菜单 CSV，用波士顿矩阵分类（Star/Plow Horse/Puzzle/Dog）
- 竞品分析、顾客评价情感分析
- 生成 HTML 报告
- 启动命令：`python -X utf8 main.py` 或 `uvicorn app:app --host 0.0.0.0 --port 8000`
- Web 界面：http://localhost:8000

**CSV 数据格式：**
- 菜单：`dish_name, category, price, cost, monthly_orders, rating`
- 评价：`dish_name, review_text`
- 竞品：`restaurant_name, dish_name, category, price, rating, monthly_orders`

### 2. 每日餐饮情报系统（新增）
位于 `daily_intel/` 目录，每天早上8点自动运行。

**目标：** 采集 TO C 消费行为信号（不要行业报告/白皮书/宏观分析）

**采集方向（6个固定 + 用户自定义）：**
- 小红书种草：餐厅爆款打卡内容
- 抖音爆款：餐饮创意新玩法
- 大众点评热门：消费者热评和必点菜
- 体验与互动：餐厅互动仪式感创新
- 打法与模式：餐饮新模式门店爆款打法
- 特色产品：新中式茶饮烘焙网红单品

**用户自定义方向：** 编辑 `daily_intel/topics.json` 的 `custom_directions` 字段

**数据质量要求（重要）：**
- 只保留 48 小时内的新内容（`is_fresh()` 函数过滤）
- 自动排除行业报告/白皮书/峰会/融资等 B 端词
- 宁可条数少，不注水。无新内容时展示空状态页面

**运行命令：**
```
python -X utf8 daily_intel/run_daily.py
```

**报告输出：** `daily_intel/reports/intel_YYYY-MM-DD.html`，自动在浏览器打开

## AI 接口配置
- **使用 DeepSeek**（OpenAI 兼容接口），不是 Anthropic/Claude
- 配置文件：`.env`（不进 Git，需在每台机器单独创建）
- API Base URL：`https://api.deepseek.com`
- 模型：`deepseek-chat`

**.env 文件内容（每台新电脑需手动创建）：**
```
DEEPSEEK_API_KEY=你的Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## Python 环境
- Python 3.12，路径：`C:\Users\{用户名}\AppData\Local\Programs\Python\Python312\python.exe`
- 依赖安装：`pip install -r requirements.txt` + `pip install beautifulsoup4 lxml openai`

## 定时任务
- 通过 Claude Code 的 Scheduled Tasks 功能设置（左侧边栏 Scheduled 区域）
- 任务名：`daily-restaurant-intel`，每天 08:00 自动运行
- 注意：Claude Code 桌面端必须保持打开状态才会触发

## 已知限制
- 抖音、小红书、大众点评无公开 API，无法直接抓取平台内容
- 目前通过 Google News RSS + 精准关键词曲线获取相关资讯
- 如需真正的平台一手数据，需付费接入飞瓜数据（抖音）/ 千瓜数据（小红书）

## 关键文件
```
restaurant-analyzer/
├── app.py                    # FastAPI 后端（菜单分析 Web 界面）
├── main.py                   # 命令行入口（菜单分析）
├── config/settings.py        # 配置（DeepSeek API Key 从 .env 读取）
├── daily_intel/
│   ├── run_daily.py          # 每日情报入口（直接运行这个）
│   ├── collector.py          # 采集逻辑（Google News RSS）
│   ├── reporter.py           # 报告生成（HTML + DeepSeek AI 提炼）
│   └── topics.json           # 用户自定义采集方向（在这里加新词）
├── src/
│   ├── analysis/             # 菜单分析、情感分析
│   └── output/               # 报告生成
└── .env                      # API Key（不进 Git，每台机器单独配置）
```
