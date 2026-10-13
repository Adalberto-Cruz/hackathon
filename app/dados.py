"""
Carrega os CSVs gerados por scripts/gerar_dados.py e expõe DataFrames prontos.
"""

import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# colunas minimas obrigatorias por arquivo
_COLUNAS_OBRIGATORIAS = {
    "clientes.csv":   {"id_cliente", "nome", "cidade", "segmento"},
    "vendedores.csv": {"id_vendedor", "nome", "regiao", "meta_mensal"},
    "pedidos.csv":    {"id_pedido", "id_cliente", "id_vendedor", "produto",
                       "quantidade", "preco_unitario", "total", "status"},
    "maquinas.csv":   {"id_maquina", "status", "localizacao",
                       "ultima_manutencao", "horas_operacao"},
}


def _load(filename: str) -> pd.DataFrame | None:
    # carrega um CSV e valida colunas; retorna None em caso de qualquer problema
    path = os.path.join(_DATA_DIR, filename)
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        logger.warning("Arquivo nao encontrado: %s", path)
        return None
    except pd.errors.EmptyDataError:
        logger.warning("Arquivo vazio: %s", path)
        return None
    except pd.errors.ParserError as e:
        logger.warning("Erro ao parsear %s: %s", filename, e)
        return None
    except UnicodeDecodeError as e:
        logger.warning("Erro de encoding em %s: %s", filename, e)
        return None

    # valida colunas obrigatorias
    obrig = _COLUNAS_OBRIGATORIAS.get(filename, set())
    faltando = obrig - set(df.columns)
    if faltando:
        logger.warning("Colunas faltando em %s: %s", filename, faltando)
        return None

    return df


# DataFrames globais
clientes: pd.DataFrame | None = None
vendedores: pd.DataFrame | None = None
pedidos: pd.DataFrame | None = None
maquinas: pd.DataFrame | None = None


def carregar_todos() -> None:
    # carrega cada CSV de forma independente; falha em um nao afeta os outros
    global clientes, vendedores, pedidos, maquinas
    clientes  = _load("clientes.csv")
    vendedores = _load("vendedores.csv")
    pedidos   = _load("pedidos.csv")
    maquinas  = _load("maquinas.csv")


# carrega ao importar
carregar_todos()


# ── utilitários de resumo ──────────────────────────────────────────────────────

def resumo_pedidos() -> dict:
    if pedidos is None:
        return {}
    return {
        "total_pedidos": int(len(pedidos)),
        "receita_total": float(pedidos["total"].sum()),
        "ticket_medio": float(pedidos["total"].mean()),
        "pedidos_por_status": pedidos["status"].value_counts().to_dict(),
    }


def top_vendedores(n: int = 5) -> list[dict]:
    if pedidos is None or vendedores is None:
        return []
    merged = pedidos.merge(vendedores, on="id_vendedor")
    ranking = (
        merged.groupby(["id_vendedor", "nome"])["total"]
        .sum()
        .reset_index()
        .sort_values("total", ascending=False)
        .head(n)
    )
    return ranking.rename(columns={"total": "receita"}).to_dict(orient="records")


def maquinas_por_status() -> dict:
    if maquinas is None:
        return {}
    return maquinas["status"].value_counts().to_dict()
