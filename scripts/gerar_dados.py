"""
Gera dados fictícios: clientes, vendedores, pedidos e máquinas.
Execute: python scripts/gerar_dados.py
Os CSVs são salvos em data/
"""

import os
import random
import csv
from datetime import datetime, timedelta

SEED = 42
random.seed(SEED)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────────

def rand_date(start: datetime, end: datetime) -> str:
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


def write_csv(filename: str, rows: list[dict]) -> None:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  - {filename} ({len(rows)} registros)")


# ── clientes ─────────────────────────────────────────────────────────────────

NOMES = [
    "Ana Lima", "Bruno Souza", "Carlos Melo", "Diana Rocha", "Eduardo Neves",
    "Fernanda Costa", "Gabriel Pinto", "Helena Cruz", "Igor Martins", "Julia Alves",
    "Leonardo Silva", "Mariana Gomes", "Nicolas Ferreira", "Olivia Santos",
    "Pedro Oliveira", "Queila Barros", "Rafael Cunha", "Sara Vieira",
    "Tiago Cardoso", "Ursula Moura",
]
CIDADES = ["São Paulo", "Rio de Janeiro", "Curitiba", "Belo Horizonte", "Porto Alegre",
           "Salvador", "Fortaleza", "Recife", "Manaus", "Brasília"]
SEGMENTOS = ["Supermercado", "Atacado", "Cafeteria", "Padaria", "Escritorio", "Hotel"]


def gerar_clientes(n: int = 50) -> list[dict]:
    clientes = []
    for i in range(1, n + 1):
        clientes.append({
            "id_cliente": i,
            "nome": random.choice(NOMES) + f" {i}",
            "cidade": random.choice(CIDADES),
            "segmento": random.choice(SEGMENTOS),
            "data_cadastro": rand_date(datetime(2025, 1, 1), datetime(2026, 9, 30)),
        })
    return clientes


# ── vendedores ───────────────────────────────────────────────────────────────

VENDEDORES_NOMES = [
    "Alice Ramos", "Bernardo Faria", "Camila Lopes", "Diego Assis",
    "Elaine Duarte", "Fábio Tavares", "Giovanna Nunes", "Henrique Vaz",
    "Isabela Correia", "João Peixoto",
]
REGIOES = ["Sul", "Sudeste", "Norte", "Nordeste", "Centro-Oeste"]


def gerar_vendedores(n: int = 10) -> list[dict]:
    vendedores = []
    for i in range(1, n + 1):
        vendedores.append({
            "id_vendedor": i,
            "nome": VENDEDORES_NOMES[i - 1],
            "regiao": random.choice(REGIOES),
            "meta_mensal": random.randint(20_000, 80_000),
        })
    return vendedores


# ── pedidos ───────────────────────────────────────────────────────────────────

# produto → preço unitário típico (min, max)
PRODUTOS = {
    "Cafe torrado e moido 500g": (18.0, 32.0),
    "Cafe em graos 1kg": (45.0, 90.0),
    "Cafe soluvel": (22.0, 40.0),
    "Capsulas de espresso": (28.0, 55.0),
    "Capsulas de cappuccino": (30.0, 58.0),
    "Capsulas de cha": (25.0, 48.0),
    "Maquina de capsulas multibebidas": (350.0, 980.0),
}
STATUS = ["entregue", "entregue", "entregue", "cancelado", "em_transito"]


def gerar_pedidos(clientes: list[dict], vendedores: list[dict], n: int = 200) -> list[dict]:
    pedidos = []
    nomes_produto = list(PRODUTOS.keys())
    for i in range(1, n + 1):
        cliente = random.choice(clientes)
        vendedor = random.choice(vendedores)
        produto = random.choice(nomes_produto)
        preco_min, preco_max = PRODUTOS[produto]
        qtd = random.randint(1, 20)
        preco = round(random.uniform(preco_min, preco_max), 2)
        pedidos.append({
            "id_pedido": i,
            "id_cliente": cliente["id_cliente"],
            "id_vendedor": vendedor["id_vendedor"],
            "produto": produto,
            "quantidade": qtd,
            "preco_unitario": preco,
            "total": round(qtd * preco, 2),
            "status": random.choice(STATUS),
            "data_pedido": rand_date(datetime(2025, 1, 1), datetime(2026, 9, 30)),
        })
    return pedidos


# ── máquinas ──────────────────────────────────────────────────────────────────

# modelos ficticios de maquinas de cafe
MODELOS_MAQUINA = ["Multibebidas Modelo A", "Multibebidas Modelo B", "Multibebidas Modelo C"]
ESTADOS = ["operando", "operando", "operando", "manutencao", "parada"]
ERROS_COM_FALHA = ["vazamento", "aquecimento", "bomba", "sensor"]


def gerar_maquinas(clientes: list[dict], n: int = 20) -> list[dict]:
    maquinas = []
    for i in range(1, n + 1):
        cliente = random.choice(clientes)
        status = random.choice(ESTADOS)

        # maquinas paradas tem no minimo 3 falhas
        if status == "parada":
            falhas = random.randint(3, 5)
        else:
            falhas = random.randint(0, 5)

        # ultimo_erro depende do numero de falhas
        if falhas == 0:
            ultimo_erro = "nenhum"
        else:
            ultimo_erro = random.choice(ERROS_COM_FALHA)

        maquinas.append({
            "id_maquina": i,
            "tipo": random.choice(MODELOS_MAQUINA),
            "id_cliente": cliente["id_cliente"],
            "localizacao": cliente["cidade"],
            "status": status,
            "ultima_manutencao": rand_date(datetime(2025, 1, 1), datetime(2026, 9, 30)),
            "horas_operacao": random.randint(100, 8000),
            "falhas_90d": falhas,
            "ultimo_erro": ultimo_erro,
        })
    return maquinas


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Gerando dados ficticios...")
    clientes = gerar_clientes()
    vendedores = gerar_vendedores()
    pedidos = gerar_pedidos(clientes, vendedores)
    maquinas = gerar_maquinas(clientes)

    write_csv("clientes.csv", clientes)
    write_csv("vendedores.csv", vendedores)
    write_csv("pedidos.csv", pedidos)
    write_csv("maquinas.csv", maquinas)
    print("Concluido! Arquivos em data/")
