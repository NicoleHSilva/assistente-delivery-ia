from openai import OpenAI

from src.config import LLM_API_KEY, LLM_BASE_URL

if not LLM_API_KEY:
    raise SystemExit("Defina LLM_API_KEY no arquivo .env")

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

for modelo in sorted(client.models.list().data, key=lambda m: m.id):
    print(modelo.id)