import json

from openai import APIError, OpenAI

from src.agent.guardrails import resposta_degenerada
from src.agent.prompts import montar_system_prompt
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from src.rag.retriever import Retriever
from src.rag.sinonimos import expandir_consulta
from src.tools.order_tools import FERRAMENTAS, executar_ferramenta

MAX_PASSOS = 5  # no máximo 5 idas e vindas com o modelo por mensagem
MAX_HISTORICO = 12  # guarda só as últimas 12 mensagens da conversa
MAX_TOKENS = 1500  # limite de tamanho de cada resposta do modelo


class Agente:
    def __init__(self, cliente_id: int, debug: bool = False, retriever=None, client=None):
        if client is None and not LLM_API_KEY:
            raise ValueError("Defina LLM_API_KEY no arquivo .env")
        self.cliente_id = cliente_id  # vem da sessão, nunca do modelo
        self.debug = debug
        self.retriever = retriever or Retriever()
        # max_retries: tenta de novo sozinho em erros temporários (429, 503)
        self.client = client or OpenAI(
            api_key=LLM_API_KEY, base_url=LLM_BASE_URL, max_retries=4
        )
        self.historico: list[dict] = []

    def _log(self, texto: str) -> None:
        if self.debug:
            print(f"  [debug] {texto}")

    def _executar(self, chamada) -> dict:
        """Executa a ferramenta que o modelo pediu."""
        nome = chamada.function.name
        try:
            argumentos = json.loads(chamada.function.arguments or "{}")
            if not isinstance(argumentos, dict):
                raise ValueError("argumentos não são um objeto")
        except (json.JSONDecodeError, ValueError):
            argumentos = {}
            resultado = {"erro": "Argumentos em formato inválido."}
        else:
            resultado = executar_ferramenta(nome, argumentos, self.cliente_id)
        self._log(f"ferramenta: {nome}({argumentos}) -> {resultado}")
        return resultado

    def _guardar(self, pergunta: str, resposta: str) -> None:
        self.historico.append({"role": "user", "content": pergunta})
        self.historico.append({"role": "assistant", "content": resposta})
        self.historico = self.historico[-MAX_HISTORICO:]
        # A conversa guardada sempre começa com uma mensagem do cliente
        while self.historico and self.historico[0]["role"] != "user":
            self.historico.pop(0)

    def responder(self, mensagem: str) -> str:
        # 1. Busca nas políticas (com as palavras das políticas acrescentadas)
        # Inclui as 2 últimas mensagens anteriores do cliente na busca:
        # respostas curtas como "37" ou "sim" não têm contexto sozinhas
        anteriores = [m["content"] for m in self.historico if m["role"] == "user"][-2:]
        consulta = " ".join([*anteriores, mensagem])
        trechos = self.retriever.buscar(expandir_consulta(consulta), k=3)
        for t in trechos:
            self._log(f"busca: [{t.pontuacao}] {t.titulo} > {t.secao}")
        if not trechos:
            self._log("busca: nenhum trecho relevante")

        # 2. Monta a conversa: regras + trechos, histórico e a nova mensagem
        mensagens = [
            {"role": "system", "content": montar_system_prompt(trechos)},
            *self.historico,
            {"role": "user", "content": mensagem},
        ]

        # 3. Loop: o modelo responde ou pede ferramentas
        resposta_final = ""
        for _ in range(MAX_PASSOS):
            resposta = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=mensagens,
                tools=FERRAMENTAS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=MAX_TOKENS,
            )
            msg = resposta.choices[0].message

            if not msg.tool_calls:  # respondeu em texto
                texto = (msg.content or "").strip()
                if resposta_degenerada(texto):
                    self._log("resposta inválida (vazia ou só reticências): tentando de novo")
                    continue  # gasta um passo e pede de novo
                resposta_final = texto
                break

            # Registra o pedido do modelo e devolve o resultado de cada ferramenta
            mensagens.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": chamada.id,
                            "type": "function",
                            "function": {
                                "name": chamada.function.name,
                                "arguments": chamada.function.arguments,
                            },
                        }
                        for chamada in msg.tool_calls
                    ],
                }
            )
            for chamada in msg.tool_calls:
                resultado = self._executar(chamada)
                mensagens.append(
                    {
                        "role": "tool",
                        "tool_call_id": chamada.id,
                        "content": json.dumps(resultado, ensure_ascii=False),
                    }
                )

        if not resposta_final:
            resposta_final = (
                "Desculpe, não consegui concluir sua solicitação agora. "
                "Pode tentar de novo?"
            )

        self._guardar(mensagem, resposta_final)
        return resposta_final


def main() -> None:
    entrada = input("Entrar como qual cliente? (1 a 10, Enter = 2): ").strip()
    cliente_id = int(entrada) if entrada.isdigit() else 2
    agente = Agente(cliente_id=cliente_id, debug=True)
    print(f"\nAtendimento iniciado como cliente {cliente_id}. Enter vazio para sair.")
    while True:
        mensagem = input("\nVocê: ").strip()
        if not mensagem:
            break
        try:
            print(f"\nAssistente: {agente.responder(mensagem)}")
        except APIError as erro:
            print(f"\n[erro na API do LLM: {erro}]")


if __name__ == "__main__":
    main()