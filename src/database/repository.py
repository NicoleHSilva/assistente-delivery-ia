import sqlite3
from contextlib import closing

from src.config import DB_PATH

_SELECT_PEDIDO = """
    SELECT p.id, p.cliente_id, c.nome AS cliente, r.nome AS restaurante,
           p.status, p.valor, p.criado_em, p.previsto_para, p.entregue_em
    FROM pedidos p
    JOIN clientes c ON c.id = p.cliente_id
    JOIN restaurantes r ON r.id = p.restaurante_id
"""


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # permite acessar colunas pelo nome
    return conn


def buscar_pedido(pedido_id: int) -> dict | None:
    with closing(_conectar()) as conn:
        linha = conn.execute(
            _SELECT_PEDIDO + " WHERE p.id = ?", (pedido_id,)
        ).fetchone()
    return dict(linha) if linha else None


def listar_pedidos_cliente(cliente_id: int) -> list[dict]:
    with closing(_conectar()) as conn:
        linhas = conn.execute(
            _SELECT_PEDIDO + " WHERE p.cliente_id = ? ORDER BY p.criado_em DESC",
            (cliente_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


if __name__ == "__main__":
    print(buscar_pedido(1))
    print(f"Pedidos do cliente 1: {len(listar_pedidos_cliente(1))}")