"""
Interface Streamlit — chat + painel de dados.
Execute: streamlit run front/app.py
"""

# carrega o .env antes de tudo
from dotenv import load_dotenv
load_dotenv()

import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── configuração da página ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Hackathon AI Agent",
    layout="wide",
)

st.title("Hackathon AI Agent")
st.caption("Analise de dados da cafeteria com IA")

# ── inicializa histórico ──────────────────────────────────────────────────────

if "historico" not in st.session_state:
    st.session_state.historico: list[dict] = []


# ── helpers ───────────────────────────────────────────────────────────────────

def chamar_api_chat(pergunta: str) -> str:
    try:
        resp = requests.post(
            f"{API_URL}/chat",
            json={"pergunta": pergunta, "historico": st.session_state.historico},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["resposta"]
    except requests.exceptions.ConnectionError:
        return "Erro: nao foi possivel conectar a API. Certifique-se de que ela esta rodando."
    except Exception as e:
        return f"Erro: {e}"


def carregar_resumo() -> dict | None:
    try:
        resp = requests.get(f"{API_URL}/dados", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def carregar_health() -> dict | None:
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ── layout: sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Painel de Dados")

    health = carregar_health()
    if health:
        status_api = "ok" if health.get("dados_carregados") else "sem dados"
        st.markdown(f"**API:** {health.get('status', 'desconhecido')} ({status_api})")
        reg = health.get("registros", {})
        st.markdown(
            f"- Clientes: **{reg.get('clientes', 0)}**\n"
            f"- Vendedores: **{reg.get('vendedores', 0)}**\n"
            f"- Pedidos: **{reg.get('pedidos', 0)}**\n"
            f"- Maquinas: **{reg.get('maquinas', 0)}**"
        )
    else:
        st.warning("API indisponivel")

    st.divider()

    resumo = carregar_resumo()
    if resumo:
        rp = resumo.get("resumo_pedidos", {})
        st.subheader("Pedidos")
        col1, col2 = st.columns(2)
        col1.metric("Total", rp.get("total_pedidos", 0))
        col2.metric("Receita", f"R$ {rp.get('receita_total', 0):,.0f}")
        st.metric("Ticket Médio", f"R$ {rp.get('ticket_medio', 0):,.2f}")

        st.subheader("Top Vendedores")
        for v in resumo.get("top_vendedores", []):
            st.markdown(f"**{v['nome']}** — R$ {v['receita']:,.2f}")

        st.subheader("Máquinas")
        for status, qtd in resumo.get("maquinas_por_status", {}).items():
            st.markdown(f"- {status}: **{qtd}**")

    if st.button("Atualizar painel"):
        st.rerun()

    st.divider()
    if st.button("Limpar conversa"):
        st.session_state.historico = []
        st.rerun()


# ── layout: chat ──────────────────────────────────────────────────────────────

chat_container = st.container()

with chat_container:
    for msg in st.session_state.historico:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

pergunta = st.chat_input("Faça uma pergunta sobre os dados…")

if pergunta:
    # Exibe mensagem do usuário
    with st.chat_message("user"):
        st.markdown(pergunta)

    # Chama o agente
    with st.chat_message("assistant"):
        with st.spinner("Pensando…"):
            resposta = chamar_api_chat(pergunta)
        st.markdown(resposta)

    # Atualiza histórico
    st.session_state.historico.append({"role": "user", "content": pergunta})
    st.session_state.historico.append({"role": "assistant", "content": resposta})
