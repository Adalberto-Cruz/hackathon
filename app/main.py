"""
API FastAPI — pontos de entrada:
  GET  /health       → status da aplicação
  POST /chat         → pergunta para o agente
  GET  /dados        → resumo dos dados carregados
"""

# carrega o .env antes de qualquer import de app.*
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import dados
from app.agente import responder

app = FastAPI(
    title="Hackathon AI Agent API",
    description="API de análise de dados com agente LLM.",
    version="1.0.0",
)


# ── schemas ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    pergunta: str
    historico: list[dict] | None = None  # lista de {role, content}


class ChatResponse(BaseModel):
    resposta: str


# ── rotas ──────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
def health() -> dict:
    """Verifica se a API está no ar e se os dados foram carregados."""
    dados_ok = dados.pedidos is not None
    return {
        "status": "ok",
        "dados_carregados": dados_ok,
        "registros": {
            "clientes": len(dados.clientes) if dados.clientes is not None else 0,
            "vendedores": len(dados.vendedores) if dados.vendedores is not None else 0,
            "pedidos": len(dados.pedidos) if dados.pedidos is not None else 0,
            "maquinas": len(dados.maquinas) if dados.maquinas is not None else 0,
        },
    }


@app.post("/chat", response_model=ChatResponse, tags=["agente"])
def chat(req: ChatRequest) -> ChatResponse:
    """Envia uma pergunta ao agente e retorna a resposta."""
    if not req.pergunta.strip():
        raise HTTPException(status_code=400, detail="Pergunta não pode ser vazia.")
    resposta = responder(req.pergunta, req.historico)
    return ChatResponse(resposta=resposta)


@app.get("/dados", tags=["dados"])
def resumo_dados() -> dict:
    """Retorna um resumo analítico dos dados carregados."""
    if dados.pedidos is None:
        raise HTTPException(
            status_code=503,
            detail="Dados não carregados. Execute `python scripts/gerar_dados.py` primeiro.",
        )
    return {
        "resumo_pedidos": dados.resumo_pedidos(),
        "top_vendedores": dados.top_vendedores(5),
        "maquinas_por_status": dados.maquinas_por_status(),
    }
