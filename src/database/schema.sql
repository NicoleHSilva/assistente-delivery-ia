PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS chamados;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS restaurantes;
DROP TABLE IF EXISTS clientes;

CREATE TABLE clientes (
    id    INTEGER PRIMARY KEY,
    nome  TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE restaurantes (
    id        INTEGER PRIMARY KEY,
    nome      TEXT NOT NULL,
    categoria TEXT NOT NULL
);

CREATE TABLE pedidos (
    id             INTEGER PRIMARY KEY,
    cliente_id     INTEGER NOT NULL REFERENCES clientes(id),
    restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id),
    status         TEXT NOT NULL
                   CHECK (status IN ('preparando', 'a_caminho', 'entregue', 'cancelado')),
    valor          REAL NOT NULL,
    criado_em      TEXT NOT NULL,
    previsto_para  TEXT NOT NULL,
    entregue_em    TEXT
);

CREATE TABLE chamados (
    id         INTEGER PRIMARY KEY,
    pedido_id  INTEGER NOT NULL REFERENCES pedidos(id),
    motivo     TEXT NOT NULL,
    criado_em  TEXT NOT NULL
);