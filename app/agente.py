"""
Agente com ferramentas que consultam os DataFrames e orquestram respostas do LLM.
"""

import json
import logging
from typing import Any

from app import dados
# importa configuracoes ja lidas pelo llm.py para nao duplicar os.getenv
from app.llm import (
    chat, system_prompt, formatar_reais,
    OPENAI_API_KEY, OPENAI_MODEL, USE_OLLAMA,
)

logger = logging.getLogger(__name__)

# ── definição das ferramentas ─────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "resumo_pedidos",
            "description": (
                "Retorna um resumo geral dos pedidos de produtos de cafe: "
                "total, receita, ticket medio e contagem por status."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_vendedores",
            "description": "Retorna os N vendedores da empresa de cafe com maior receita total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Quantidade de vendedores a retornar (padrao 5).",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "maquinas_por_status",
            "description": (
                "Retorna a contagem de maquinas de capsulas multibebidas "
                "agrupadas por status (operando, manutencao, parada)."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_clientes",
            "description": "Lista clientes (supermercados, cafeterias, hoteis etc.) com filtro opcional por cidade ou segmento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cidade": {"type": "string", "description": "Filtrar por cidade."},
                    "segmento": {"type": "string", "description": "Filtrar por segmento (ex: Cafeteria, Hotel)."},
                    "limite": {"type": "integer", "description": "Maximo de registros (padrao 10)."},
                },
                "required": [],
            },
        },
    },
]


# ── execução das ferramentas ──────────────────────────────────────────────────

def _executar_ferramenta(nome: str, args: dict) -> Any:
    if nome == "resumo_pedidos":
        return dados.resumo_pedidos()

    if nome == "top_vendedores":
        # converte e clipa o valor de n
        try:
            n = max(1, min(50, int(args.get("n", 5))))
        except (TypeError, ValueError):
            n = 5
        return dados.top_vendedores(n)

    if nome == "maquinas_por_status":
        return dados.maquinas_por_status()

    if nome == "listar_clientes":
        if dados.clientes is None:
            return []
        df = dados.clientes.copy()
        if cidade := args.get("cidade"):
            df = df[df["cidade"].str.lower() == cidade.lower()]
        if segmento := args.get("segmento"):
            df = df[df["segmento"].str.lower() == segmento.lower()]
        try:
            limite = max(1, min(50, int(args.get("limite", 10))))
        except (TypeError, ValueError):
            limite = 10
        return df.head(limite).to_dict(orient="records")

    return {"erro": f"Ferramenta '{nome}' nao reconhecida."}


# ── orquestrador principal ────────────────────────────────────────────────────

def responder(pergunta: str, historico: list[dict] | None = None) -> str:
    """
    Recebe uma pergunta e retorna a resposta do agente.
    historico e uma lista de mensagens {role, content} anteriores.
    """
    mensagens: list[dict] = [{"role": "system", "content": system_prompt()}]
    if historico:
        mensagens.extend(historico)
    mensagens.append({"role": "user", "content": pergunta})

    # pula tool calling se estiver em modo Ollama ou sem chave OpenAI
    usar_tool_calling = (not USE_OLLAMA) and bool(OPENAI_API_KEY)

    if usar_tool_calling:
        try:
            from openai import OpenAI  # type: ignore[import]

            client = OpenAI(api_key=OPENAI_API_KEY, timeout=20, max_retries=1)

            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=mensagens,  # type: ignore[arg-type]
                tools=TOOLS,  # type: ignore[arg-type]
                tool_choice="auto",
            )
            msg = resp.choices[0].message

            # sem tool calls: retorna direto
            if not msg.tool_calls:
                return msg.content or ""

            mensagens.append(msg)  # type: ignore[arg-type]

            for tc in msg.tool_calls:
                # json.loads seguro
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                resultado = _executar_ferramenta(tc.function.name, args)
                mensagens.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(resultado, ensure_ascii=False, default=str),
                    }
                )

            resp2 = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=mensagens,  # type: ignore[arg-type]
            )
            return resp2.choices[0].message.content or ""

        except Exception as e:
            logger.warning("Tool calling falhou (%s). Usando contexto injetado.", e)

    # fallback: injeta dados no contexto e chama chat() com historico
    contexto = _contexto_resumido()
    mensagens_ctx: list[dict] = [
        {"role": "system", "content": system_prompt() + "\n\n" + contexto},
    ]
    if historico:
        mensagens_ctx.extend(historico)
    mensagens_ctx.append({"role": "user", "content": pergunta})

    return chat(mensagens_ctx, pergunta=pergunta)


def _contexto_resumido() -> str:
    # monta contexto textual dos dados para o fallback sem tool_calls
    partes = ["## Dados disponiveis\n"]

    resumo = dados.resumo_pedidos()
    if resumo:
        partes.append(
            f"Pedidos: {resumo.get('total_pedidos')} | "
            f"Receita total: {formatar_reais(resumo.get('receita_total', 0))} | "
            f"Ticket medio: {formatar_reais(resumo.get('ticket_medio', 0))}\n"
            f"Status: {resumo.get('pedidos_por_status')}\n"
        )

    top = dados.top_vendedores(3)
    if top:
        partes.append("Top 3 vendedores: " + ", ".join(
            f"{v['nome']} ({formatar_reais(v['receita'])})" for v in top
        ) + "\n")

    maq = dados.maquinas_por_status()
    if maq:
        partes.append(f"Maquinas: {maq}\n")

    return "\n".join(partes)
