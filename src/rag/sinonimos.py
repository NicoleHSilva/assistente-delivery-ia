from src.rag.retriever import normalizar

# Palavras que o cliente costuma usar (já reduzidas a 5 letras, como o
# retriever faz) e as palavras que as políticas usam para o mesmo assunto.
SINONIMOS = {
    "demor": "atraso atrasou",  # demorando, demora, demorou
    "tempo": "prazo",
    "pedir": "solicitar",
    "devol": "reembolso",  # devolução, devolver
    "dinhe": "reembolso",  # dinheiro de volta
    "estor": "reembolso",  # estorno
    "frio": "qualidade",
    "fria": "qualidade",
}


def expandir_consulta(pergunta: str) -> str:
    """Acrescenta à pergunta as palavras que as políticas usam."""
    extras: list[str] = []
    for token in normalizar(pergunta):
        extras.extend(SINONIMOS.get(token, "").split())
    return f"{pergunta} {' '.join(extras)}".strip()