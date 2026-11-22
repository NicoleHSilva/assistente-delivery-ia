from datetime import datetime

from src.database import repository

FORMATO_DATA = "%Y-%m-%d %H:%M:%S"
TAMANHO_MAXIMO_MOTIVO = 500


# ---------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------
def _como_data(texto: str) -> datetime:
    return datetime.strptime(texto, FORMATO_DATA)


def _como_inteiro(valor) -> int | None:
    """O modelo às vezes manda '5' (texto) em vez de 5. Aceita os dois."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _calcular_atraso(pedido: dict, agora: datetime | None = None) -> int:
    """Minutos de atraso. Calculado aqui porque modelos erram conta de datas."""
    agora = agora or datetime.now()
    previsto = _como_data(pedido["previsto_para"])

    if pedido["status"] == "entregue":
        referencia = _como_data(pedido["entregue_em"])
    elif pedido["status"] in ("preparando", "a_caminho"):
        referencia = agora  # ainda não chegou: compara com o horário de agora
    else:  # cancelado
        return 0

    return max(0, int((referencia - previsto).total_seconds() // 60))


def _pedido_do_cliente(cliente_id: int, pedido_id) -> dict | None:
    """Devolve o pedido só se ele existir E for deste cliente."""
    pedido_id = _como_inteiro(pedido_id)
    if pedido_id is None:
        return None
    pedido = repository.buscar_pedido(pedido_id)
    if pedido is None or pedido["cliente_id"] != cliente_id:
        return None
    return pedido


# Mesma resposta para "não existe" e "é de outro cliente":
# assim ninguém descobre que o pedido existe.
_ERRO_PEDIDO = {"erro": "Pedido não encontrado para este cliente."}


# ---------------------------------------------------------------
# As ferramentas (o cliente_id vem da sessão, nunca do modelo)
# ---------------------------------------------------------------
def consultar_pedido(cliente_id: int, pedido_id) -> dict:
    pedido = _pedido_do_cliente(cliente_id, pedido_id)
    if pedido is None:
        return _ERRO_PEDIDO
    return {
        "pedido_id": pedido["id"],
        "restaurante": pedido["restaurante"],
        "status": pedido["status"],
        "valor": pedido["valor"],
        "criado_em": pedido["criado_em"],
        "previsto_para": pedido["previsto_para"],
        "entregue_em": pedido["entregue_em"],
        "atraso_minutos": _calcular_atraso(pedido),
    }


def listar_meus_pedidos(cliente_id: int, limite: int = 5) -> dict:
    limite = _como_inteiro(limite) or 5
    limite = max(1, min(limite, 10))
    pedidos = repository.listar_pedidos_cliente(cliente_id)[:limite]
    return {
        "pedidos": [
            {
                "pedido_id": p["id"],
                "restaurante": p["restaurante"],
                "status": p["status"],
                "valor": p["valor"],
                "criado_em": p["criado_em"],
            }
            for p in pedidos
        ]
    }


def abrir_chamado(cliente_id: int, pedido_id, motivo: str = "") -> dict:
    pedido = _pedido_do_cliente(cliente_id, pedido_id)
    if pedido is None:
        return _ERRO_PEDIDO
    motivo = (motivo or "").strip()
    if not motivo:
        return {"erro": "Informe o motivo do chamado."}
    if len(motivo) > TAMANHO_MAXIMO_MOTIVO:
        return {"erro": f"O motivo pode ter no máximo {TAMANHO_MAXIMO_MOTIVO} caracteres."}

    chamado_id = repository.criar_chamado(pedido["id"], motivo)
    return {"chamado_id": chamado_id, "mensagem": "Chamado aberto com sucesso."}


# ---------------------------------------------------------------
# O que o modelo enxerga: nome, descrição e parâmetros.
# Repare que NENHUMA ferramenta pede cliente_id.
# ---------------------------------------------------------------
FERRAMENTAS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_pedido",
            "description": (
                "Consulta o status, os horários e os minutos de atraso de um "
                "pedido do cliente atual. Use quando o cliente perguntar sobre "
                "um pedido específico."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "Número do pedido."}
                },
                "required": ["pedido_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_meus_pedidos",
            "description": (
                "Lista os pedidos mais recentes do cliente atual. Use quando o "
                "cliente não souber o número do pedido."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Quantos pedidos listar (de 1 a 10). Padrão: 5.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_chamado",
            "description": (
                "Abre um chamado de atendimento para um pedido do cliente atual. "
                "Use só depois de entender o problema e quando o cliente pedir "
                "ou a política indicar que é necessário."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {"type": "integer", "description": "Número do pedido."},
                    "motivo": {
                        "type": "string",
                        "description": "Resumo do problema, em uma ou duas frases.",
                    },
                },
                "required": ["pedido_id", "motivo"],
            },
        },
    },
]

_FUNCOES = {
    "consultar_pedido": consultar_pedido,
    "listar_meus_pedidos": listar_meus_pedidos,
    "abrir_chamado": abrir_chamado,
}


def executar_ferramenta(nome: str, argumentos: dict, cliente_id: int) -> dict:
    """Executa a ferramenta que o modelo pediu, em nome do cliente da sessão."""
    funcao = _FUNCOES.get(nome)
    if funcao is None:
        return {"erro": f"Ferramenta desconhecida: {nome}"}
    # Descarta qualquer cliente_id que o modelo tente passar
    argumentos = {k: v for k, v in (argumentos or {}).items() if k != "cliente_id"}
    try:
        return funcao(cliente_id=cliente_id, **argumentos)
    except TypeError:
        return {"erro": "Argumentos inválidos para a ferramenta."}


if __name__ == "__main__":
    import json

    # (ferramenta, argumentos, cliente da sessão)
    casos = [
        ("listar_meus_pedidos", {}, 2),
        ("consultar_pedido", {"pedido_id": 1}, 2),  # pedido do próprio cliente
        ("consultar_pedido", {"pedido_id": 1}, 3),  # pedido de OUTRO cliente
        ("consultar_pedido", {"pedido_id": 999}, 2),  # não existe
        ("consultar_pedido", {"pedido_id": "1", "cliente_id": 3}, 2),  # tentativa de fraude
        ("abrir_chamado", {"pedido_id": 1, "motivo": "Teste da ferramenta"}, 2),
        ("abrir_chamado", {"pedido_id": 1, "motivo": ""}, 2),
        ("ferramenta_inventada", {}, 2),
    ]
    for nome, args, cliente in casos:
        print(f"\n> {nome}({args}) como cliente {cliente}")
        print(json.dumps(executar_ferramenta(nome, args, cliente), ensure_ascii=False, indent=2))