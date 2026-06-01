"""Configuration for BRAHMO Rules Engine."""
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "brahmo_rules_engine")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# Pipeline
DERIVABILITY_THRESHOLD = float(os.getenv("DERIVABILITY_THRESHOLD", "0.7"))
MAX_CANDIDATE_SET = int(os.getenv("MAX_CANDIDATE_SET", "50"))

# App
APP_ENV = os.getenv("APP_ENV", "development")
APP_DEBUG = os.getenv("APP_DEBUG", "true").lower() == "true"