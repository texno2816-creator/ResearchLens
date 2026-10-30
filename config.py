"""Все настройки проекта. Секреты и переключатели берутся из файла .env."""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "researchlens.db")

# ---------- ИИ ----------
# Модель выбрана по итогам тестов (шаг 3): лучшая точность, меньше всего мусора, самая быстрая.
# Она одна и та же на Groq и на OpenRouter, меняется только провайдер.
LLM_MODEL = "openai/gpt-oss-20b"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# Версия правил оценки. Меняется при изменении prompts.py, чтобы не брать старые оценки из кэша.
PROMPT_VERSION = "2"

# Сколько статей ИИ оценивает за один поиск и по сколько отправляет в одном запросе
ARTICLES_TO_SCORE = 20
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "1"))
# Лимит бесплатного Groq — 8000 токенов в минуту, и один запрос не может быть больше этого.
# Поэтому: длинные аннотации обрезаем, ответ ИИ ограничиваем, а пачку собираем по «весу» текста.
MAX_ABSTRACT_CHARS = 2500        # длиннее почти не бывает (99% аннотаций короче 3300 знаков)
MAX_OUTPUT_TOKENS = 2500         # ответ ИИ вместе с рассуждением; на пачку из 5 статей хватает с запасом
REQUEST_TOKEN_LIMIT = int(os.getenv("REQUEST_TOKEN_LIMIT", "8000"))

# ---------- OpenAlex ----------
# Берём с запасом: дубликаты и статьи без аннотации заменяются следующими
OPENALEX_FETCH = 50
# Кнопка «Проверить ещё 20»: максимум статей, которые ИИ оценит по одному запросу
MAX_ARTICLES_PER_QUERY = 100
# Сколько страниц OpenAlex можно загрузить за один раз (защита от бесконечного поиска)
MAX_PAGES_PER_ROUND = 4
# Если OpenAlex нашёл меньше статей, проверяем запрос на опечатки
SPELLCHECK_BELOW = 100
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "").strip()
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()

# ---------- Категории ----------
YES_THRESHOLD = 7.5
UNCLEAR_THRESHOLD = 4.0

# ---------- Тестовый режим ----------
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-too")
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
