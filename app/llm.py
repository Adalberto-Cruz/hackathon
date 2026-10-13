"""
Camada de acesso ao LLM.
Suporta OpenAI (padrão) com fallback para modelo local via Ollama.
Nivel final de fallback: resposta_offline com dados locais.
"""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# configuracao lida uma vez na importacao
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

USE_OLLAMA: bool = os.getenv("USE_OLLAMA", "false").lower() == "true"


# ── clientes LLM ─────────────────────────────────────────────────────────────

def _openai_chat(messages: list[dict], **kwargs: Any) -> str:
    # pula imediatamente se nao ha chave configurada
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY nao configurada")

    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:
        raise RuntimeError("Pacote 'openai' nao instalado")

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=20, max_retries=1)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def _ollama_chat(messages: list[dict], **kwargs: Any) -> str:
    try:
        import requests  # type: ignore[import]
    except ImportError:
        raise RuntimeError("Pacote 'requests' nao instalado")

    payload = {"model": OLLAMA_MODEL, "messages": messages, "stream": False}
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── formatacao de moeda ───────────────────────────────────────────────────────

def formatar_reais(valor: float) -> str:
    # devolve no padrao brasileiro: R$ 59.200,22
    partes = f"{valor:,.2f}".split(".")          # ex: "59,200" e "22"
    inteiro = partes[0].replace(",", ".")         # troca separador de milhar
    centavos = partes[1]
    return f"R$ {inteiro},{centavos}"


# ── fallback offline ──────────────────────────────────────────────────────────

def resposta_offline(pergunta: str) -> str:
    # monta resposta com dados locais sem precisar de LLM
    from app import dados  # importacao tardia para evitar ciclo

    p = pergunta.lower()

    # detecta intenção por palavra-chave
    if any(k in p for k in ("vendedor", "ranking", "melhor vendedor")):
        top = dados.top_vendedores(5)
        if not top:
            return "[modo offline] Dados de vendedores nao disponiveis."
        linhas = "\n".join(
            f"  {i+1}. {v['nome']} - {formatar_reais(v['receita'])}"
            for i, v in enumerate(top)
        )
        return f"[modo offline] Top vendedores por receita:\n{linhas}"

    if any(k in p for k in ("pedido", "receita", "ticket", "faturamento")):
        r = dados.resumo_pedidos()
        if not r:
            return "[modo offline] Dados de pedidos nao disponiveis."
        status = ", ".join(f"{k}: {v}" for k, v in r.get("pedidos_por_status", {}).items())
        return (
            f"[modo offline] Resumo de pedidos:\n"
            f"  Total: {r.get('total_pedidos')}\n"
            f"  Receita total: {formatar_reais(r.get('receita_total', 0))}\n"
            f"  Ticket medio: {formatar_reais(r.get('ticket_medio', 0))}\n"
            f"  Status: {status}"
        )

    if any(k in p for k in ("falha", "erro")):
        # lista as 5 maquinas com mais falhas nos ultimos 90 dias
        df = dados.maquinas
        colunas_ok = (
            df is not None
            and "falhas_90d" in df.columns
            and "ultimo_erro" in df.columns
        )
        if not colunas_ok:
            # cai no comportamento de status se nao tiver os dados
            m = dados.maquinas_por_status()
            if not m:
                return "[modo offline] Dados de maquinas nao disponiveis."
            linhas = "\n".join(f"  {k}: {v}" for k, v in m.items())
            return f"[modo offline] Maquinas por status:\n{linhas}"
        top5 = df.sort_values("falhas_90d", ascending=False).head(5)
        linhas = []
        for _, row in top5.iterrows():
            # id_cliente pode nao existir em arquivos antigos
            cliente_info = f" | cliente {int(row['id_cliente'])}" if "id_cliente" in df.columns else ""
            linhas.append(
                f"  id {int(row['id_maquina'])} | {row['tipo']}"
                f"{cliente_info} | {row['localizacao']}"
                f" | falhas 90d: {int(row['falhas_90d'])} | ultimo erro: {row['ultimo_erro']}"
            )
        return f"[modo offline] Top 5 maquinas com mais falhas (90 dias):\n" + "\n".join(linhas)

    if any(k in p for k in ("maquina", "manutencao", "parada")):
        m = dados.maquinas_por_status()
        if not m:
            return "[modo offline] Dados de maquinas nao disponiveis."
        linhas = "\n".join(f"  {k}: {v}" for k, v in m.items())
        return f"[modo offline] Maquinas por status:\n{linhas}"

    if any(k in p for k in ("cliente", "segmento")):
        if dados.clientes is None:
            return "[modo offline] Dados de clientes nao disponiveis."
        total = len(dados.clientes)
        por_seg = dados.clientes["segmento"].value_counts().to_dict()
        linhas = "\n".join(f"  {k}: {v}" for k, v in por_seg.items())
        return f"[modo offline] Total de clientes: {total}\nPor segmento:\n{linhas}"

    # sem palavra-chave: devolve resumo geral
    r = dados.resumo_pedidos()
    top = dados.top_vendedores(3)
    m = dados.maquinas_por_status()
    partes = ["[modo offline] Resumo geral:"]
    if r:
        partes.append(
            f"  Pedidos: {r.get('total_pedidos')} | "
            f"Receita: {formatar_reais(r.get('receita_total', 0))} | "
            f"Ticket medio: {formatar_reais(r.get('ticket_medio', 0))}"
        )
    if top:
        partes.append("  Top 3 vendedores: " + ", ".join(
            f"{v['nome']} ({formatar_reais(v['receita'])})" for v in top
        ))
    if m:
        partes.append("  Maquinas: " + ", ".join(f"{k}: {v}" for k, v in m.items()))
    return "\n".join(partes)


# ── interface pública ─────────────────────────────────────────────────────────

def chat(messages: list[dict], pergunta: str = "", **kwargs: Any) -> str:
    """
    Envia mensagens ao LLM e retorna a resposta.
    Ordem: OpenAI -> Ollama -> resposta_offline.
    pergunta e usada pelo nivel offline para montar resposta por palavra-chave.
    """
    primary = _ollama_chat if USE_OLLAMA else _openai_chat
    fallback = _openai_chat if USE_OLLAMA else _ollama_chat

    try:
        return primary(messages, **kwargs)
    except Exception as primary_err:
        logger.warning("LLM primario falhou (%s). Tentando fallback...", primary_err)
        try:
            return fallback(messages, **kwargs)
        except Exception as fallback_err:
            logger.warning("Fallback LLM tambem falhou (%s). Modo offline.", fallback_err)
            return resposta_offline(pergunta)


def system_prompt() -> str:
    return (
        "Voce e um assistente inteligente de uma empresa de cafe. "
        "Voce tem acesso a dados de clientes, vendedores, pedidos de produtos de cafe "
        "e maquinas de capsulas instaladas nos clientes. "
        "Responda sempre em portugues brasileiro, de forma clara e objetiva. "
        "Quando citar numeros, formate-os de maneira legivel (ex: R$ 1.234,56)."
    )
