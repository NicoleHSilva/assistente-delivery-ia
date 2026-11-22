import random
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from src.config import DB_PATH

# Semente fixa: toda execução gera a mesma sequência "aleatória"
random.seed(42)

CLIENTES = [
    ("Ana Souza", "ana.souza@exemplo.com"),
    ("Bruno Lima", "bruno.lima@exemplo.com"),
    ("Carla Mendes", "carla.mendes@exemplo.com"),
    ("Diego Alves", "diego.alves@exemplo.com"),
    ("Elisa Rocha", "elisa.rocha@exemplo.com"),
    ("Felipe Costa", "felipe.costa@exemplo.com"),
    ("Giovana Pires", "giovana.pires@exemplo.com"),
    ("Hugo Martins", "hugo.martins@exemplo.com"),
    ("Isabela Nunes", "isabela.nunes@exemplo.com"),
    ("João Ribeiro", "joao.ribeiro@exemplo.com"),
]

RESTAURANTES = [
    ("Pizzaria Bella Massa", "Pizza"),
    ("Burger do Zé", "Hambúrguer"),
    ("Sushi Sakura", "Japonesa"),
    ("Cantina da Nona", "Italiana"),
    ("Açaí Tropical", "Sobremesas"),
    ("Marmita Caseira", "Brasileira"),
    ("Taco Loco", "Mexicana"),
    ("Padaria Pão Quente", "Padaria"),
]


def formatar(data: datetime | None) -> str | None:
    return data.isoformat(sep=" ") if data else None


def gerar_pedido(agora: datetime) -> tuple:
    cliente_id = random.randint(1, len(CLIENTES))
    restaurante_id = random.randint(1, len(RESTAURANTES))
    valor = round(random.uniform(25, 150), 2)
    status = random.choices(
        ["entregue", "a_caminho", "preparando", "cancelado"],
        weights=[60, 15, 15, 10],
    )[0]

    if status == "entregue":
        criado = agora - timedelta(hours=random.randint(3, 24 * 10))
        previsto = criado + timedelta(minutes=random.randint(30, 60))
        # Parte dos pedidos chega com atraso (até 70 min depois do previsto)
        entregue = previsto + timedelta(minutes=random.randint(-10, 70))
    elif status in ("a_caminho", "preparando"):
        criado = agora - timedelta(minutes=random.randint(10, 90))
        previsto = criado + timedelta(minutes=random.randint(30, 60))
        entregue = None
    else:  # cancelado
        criado = agora - timedelta(hours=random.randint(1, 24 * 5))
        previsto = criado + timedelta(minutes=40)
        entregue = None

    return (
        cliente_id,
        restaurante_id,
        status,
        valor,
        formatar(criado),
        formatar(previsto),
        formatar(entregue),
    )


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    agora = datetime.now().replace(microsecond=0)

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(schema)
        conn.executemany("INSERT INTO clientes (nome, email) VALUES (?, ?)", CLIENTES)
        conn.executemany(
            "INSERT INTO restaurantes (nome, categoria) VALUES (?, ?)", RESTAURANTES
        )
        pedidos = [gerar_pedido(agora) for _ in range(40)]
        conn.executemany(
            """INSERT INTO pedidos
               (cliente_id, restaurante_id, status, valor,
                criado_em, previsto_para, entregue_em)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            pedidos,
        )
        conn.commit()

    print(f"Banco criado em {DB_PATH}")
    print(f"{len(CLIENTES)} clientes, {len(RESTAURANTES)} restaurantes, {len(pedidos)} pedidos")


if __name__ == "__main__":
    main()