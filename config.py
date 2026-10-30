import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "researchlens.db")

LLM_MODEL = "openai/gpt-oss-20b"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# Bump when prompts.py changes so old cached scores are not reused
PROMPT_VERSION = "2"

ARTICLES_TO_SCORE = 20
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "1"))
# Groq free tier: 8000 tokens per minute, and one request cannot exceed it
MAX_ABSTRACT_CHARS = 2500
MAX_OUTPUT_TOKENS = 2500
REQUEST_TOKEN_LIMIT = int(os.getenv("REQUEST_TOKEN_LIMIT", "8000"))

OPENALEX_FETCH = 50
MAX_ARTICLES_PER_QUERY = 100
MAX_PAGES_PER_ROUND = 4
SPELLCHECK_BELOW = 100
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "").strip()
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()

YES_THRESHOLD = 7.5
UNCLEAR_THRESHOLD = 4.0

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-too")
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
