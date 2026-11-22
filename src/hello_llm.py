from openai import OpenAI

from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

if not LLM_API_KEY:
    raise SystemExit("Defina LLM_API_KEY no arquivo .env")

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

resposta = client.chat.completions.create(
    model=LLM_MODEL,
    messages=[
        {"role": "user", "content": "Explique em duas frases o que é um agente de IA."}
    ],
)

print(resposta.choices[0].message.content)