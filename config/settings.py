import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_CLEANED_DIR = BASE_DIR / "data" / "cleaned"
REPORTS_DIR = BASE_DIR / "reports"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# Analysis thresholds
PROFIT_MARGIN_THRESHOLD = 0.60   # above = high profitability
POPULARITY_THRESHOLD_PERCENTILE = 50  # median split for popularity

# Menu engineering categories
CATEGORY_STAR = "Star"        # 明星：高利润率 + 高点单
CATEGORY_PLOW_HORSE = "Plow Horse"  # 耕马：低利润率 + 高点单
CATEGORY_PUZZLE = "Puzzle"    # 谜题：高利润率 + 低点单
CATEGORY_DOG = "Dog"          # 瘦狗：低利润率 + 低点单

# Required columns for menu data
MENU_REQUIRED_COLUMNS = ["dish_name", "category", "price", "cost", "monthly_orders", "rating"]

# Extra paths
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "chat_history.db"
TEMPLATES_DIR = BASE_DIR / "templates"
FRONTEND_DIR = BASE_DIR / "frontend"

# Mock flag — True when no API key is configured
USE_MOCK_API = not bool(ANTHROPIC_API_KEY)
