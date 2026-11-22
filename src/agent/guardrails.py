def resposta_degenerada(texto: str) -> bool:
    """Detecta respostas vazias ou que são quase só reticências."""
    sem_espacos = "".join(texto.split())
    if not sem_espacos:
        return True
    pontos = sum(1 for c in sem_espacos if c in ".…")
    return pontos / len(sem_espacos) > 0.3