import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto: a pasta que contém "src"
BASE_DIR = Path(__file__).resolve().parent.parent

# override=True: o valor do arquivo .env vale mais do que
# qualquer variável antiga que já esteja no terminal
load_dotenv(BASE_DIR / ".env", override=True)

DB_PATH = BASE_DIR / "data" / "delivery.db"

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")