import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from src.config import BASE_DIR

KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"

# Palavras muito comuns, que não ajudam a diferenciar um trecho de outro
STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "e",
    "ou", "que", "se", "ao", "aos", "meu", "minha", "meus", "minhas",
    "eu", "ele", "ela", "foi", "ser", "ter", "mais", "mas", "como",
    "qual", "quais", "quando", "onde", "pode", "posso", "quero",
    "tenho", "tem",
}


@dataclass
class Trecho:
    fonte: str  # arquivo de onde veio
    titulo: str  # título do documento
    secao: str  # título da seção
    texto: str  # conteúdo
    pontuacao: float = 0.0


def normalizar(texto: str) -> list[str]:
    """Minúsculas, sem acentos, só letras e números, sem stopwords."""
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    palavras = re.findall(r"[a-z0-9]+", sem_acento)
    # Stemmer simples: guarda só as 5 primeiras letras.
    # Assim "atraso", "atrasou" e "atrasado" viram "atras".
    return [p[:5] for p in palavras if p not in STOPWORDS]


def _criar_trecho(fonte: str, titulo: str, secao: str, linhas: list[str]) -> Trecho:
    return Trecho(fonte=fonte, titulo=titulo, secao=secao, texto="\n".join(linhas))


def carregar_trechos(pasta: Path = KNOWLEDGE_DIR) -> list[Trecho]:
    """Lê os .md e divide cada um em trechos, um por seção (## ...)."""
    trechos: list[Trecho] = []
    for arquivo in sorted(pasta.glob("*.md")):
        titulo = arquivo.stem
        secao = None
        linhas: list[str] = []
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if linha.startswith("# "):
                titulo = linha[2:].strip()
            elif linha.startswith("## "):
                if secao and linhas:
                    trechos.append(_criar_trecho(arquivo.name, titulo, secao, linhas))
                secao = linha[3:].strip()
                linhas = []
            elif linha.strip():
                linhas.append(linha.strip())
        if secao and linhas:
            trechos.append(_criar_trecho(arquivo.name, titulo, secao, linhas))
    return trechos


class Retriever:
    """Busca de trechos relevantes usando BM25."""

    K1 = 1.5  # quanto repetir uma palavra ajuda
    B = 0.75  # quanto o tamanho do trecho pesa

    def __init__(self, trechos: list[Trecho] | None = None) -> None:
        self.trechos = trechos if trechos is not None else carregar_trechos()
        if not self.trechos:
            raise FileNotFoundError(
                f"Nenhum trecho encontrado. Confira os arquivos .md em {KNOWLEDGE_DIR}"
            )
        # Título e seção também entram na busca, porque dão contexto
        self._tokens = [
            normalizar(f"{t.titulo} {t.secao} {t.texto}") for t in self.trechos
        ]
        self._tamanho_medio = sum(len(t) for t in self._tokens) / len(self._tokens)
        # Em quantos trechos cada palavra aparece
        self._df: Counter = Counter()
        for tokens in self._tokens:
            self._df.update(set(tokens))

    def _idf(self, palavra: str) -> float:
        n = len(self.trechos)
        df = self._df.get(palavra, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def _pontuar(self, consulta: list[str], indice: int) -> float:
        tokens = self._tokens[indice]
        frequencias = Counter(tokens)
        tamanho = len(tokens)
        pontos = 0.0
        for palavra in set(consulta):
            f = frequencias.get(palavra, 0)
            if f == 0:
                continue
            numerador = f * (self.K1 + 1)
            denominador = f + self.K1 * (
                1 - self.B + self.B * tamanho / self._tamanho_medio
            )
            pontos += self._idf(palavra) * numerador / denominador
        return pontos

    def buscar(self, pergunta: str, k: int = 3) -> list[Trecho]:
        # Números (como o número do pedido) não ajudam a achar políticas
        consulta = [t for t in normalizar(pergunta) if not t.isdigit()]
        resultados = []
        for i, trecho in enumerate(self.trechos):
            pontos = self._pontuar(consulta, i)
            if pontos > 0:
                resultados.append(replace(trecho, pontuacao=round(pontos, 3)))
        resultados.sort(key=lambda t: t.pontuacao, reverse=True)
        return resultados[:k]


if __name__ == "__main__":
    retriever = Retriever()
    print(f"{len(retriever.trechos)} trechos carregados.")
    print("Digite uma pergunta (ou só Enter para sair).")
    while True:
        pergunta = input("\nPergunta: ").strip()
        if not pergunta:
            break
        resultados = retriever.buscar(pergunta)
        if not resultados:
            print("Nenhum trecho relevante encontrado.")
        for r in resultados:
            print(f"\n[{r.pontuacao}] {r.titulo} > {r.secao} ({r.fonte})")
            print(r.texto)