# Hackathon AI Agent — Documentação Técnica

## Visão Geral

Solução de análise de dados empresariais com agente LLM capaz de consultar dados de **clientes**, **vendedores**, **pedidos** e **máquinas** em linguagem natural.

---

## Arquitetura

```
┌─────────────────────┐        HTTP        ┌──────────────────────┐
│   Front (Streamlit) │ ◄────────────────► │   API (FastAPI)      │
│   front/app.py      │                    │   app/main.py        │
└─────────────────────┘                    └──────────┬───────────┘
                                                      │
                                           ┌──────────▼───────────┐
                                           │   Agente             │
                                           │   app/agente.py      │
                                           └──────────┬───────────┘
                                                      │
                                      ┌───────────────┼───────────────┐
                                      ▼               ▼               ▼
                               ┌────────────┐  ┌───────────┐  ┌────────────┐
                               │  LLM Layer │  │  Dados    │  │  Tools     │
                               │  app/llm.py│  │  app/     │  │  (funções) │
                               └────────────┘  │  dados.py │  └────────────┘
                                               └───────────┘
```

### Componentes

| Arquivo | Responsabilidade |
|---|---|
| `app/main.py` | Rotas FastAPI: `/health`, `/chat`, `/dados` |
| `app/llm.py` | Chamada ao LLM (OpenAI) com fallback para Ollama |
| `app/agente.py` | Orquestrador: interpreta a pergunta, chama ferramentas, consolida resposta |
| `app/dados.py` | Carrega os CSVs em DataFrames pandas e expõe funções de resumo |
| `front/app.py` | Interface Streamlit: chat + painel lateral com métricas |
| `scripts/gerar_dados.py` | Geração de dados fictícios (clientes, vendedores, pedidos, máquinas) |

---

## Pré-requisitos

- Python 3.11+
- Chave da OpenAI (opcional) ou Ollama instalado localmente (gratuito). Sem nenhum dos dois, o sistema funciona em modo offline.

---

## Instalação e Execução

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# edite .env com sua OPENAI_API_KEY (ou configure USE_OLLAMA=true)
```

### 3. Gerar dados fictícios

```bash
python scripts/gerar_dados.py
```

Cria a pasta `data/` com os arquivos:
- `clientes.csv` — 50 clientes (segmentos: Supermercado, Atacado, Cafeteria, Padaria, Escritorio, Hotel)
- `vendedores.csv` — 10 vendedores
- `pedidos.csv` — 200 pedidos de produtos de café (capsulas, graos, soluvel, maquinas)
- `maquinas.csv` — 20 maquinas Multibebidas com colunas `falhas_90d`, `ultimo_erro` e `id_cliente`

### 4. Subir a API

```bash
uvicorn app.main:app --reload
```

API disponível em `http://localhost:8000`.  
Documentação interativa: `http://localhost:8000/docs`

### 5. Subir o frontend

```bash
streamlit run front/app.py
```

Interface disponível em `http://localhost:8501`.

---

## Rodando sem chave da OpenAI (Ollama local)

### 1. Baixar e instalar o Ollama

Acesse https://ollama.com/download e siga as instruções para o seu sistema operacional.

### 2. Baixar o modelo

```bash
ollama pull llama3.2:3b
```

### 3. Confirmar que está no ar

```bash
ollama list
```

### 4. Configurar o .env

```
OPENAI_API_KEY=
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2:3b
```

### 5. Subir a API e o frontend normalmente

```bash
uvicorn app.main:app --reload
streamlit run front/app.py
```

**Observação:** no modo Ollama o agente não usa tool calling. Ele recebe um resumo dos dados diretamente no prompt, então as respostas são menos precisas do que na OpenAI.

**Observação:** se nem OpenAI nem Ollama estiverem disponíveis, o sistema responde em `[modo offline]` com os dados dos CSVs.

---

## Endpoints da API

### `GET /health`
Verifica se a API está no ar e quantos registros estão carregados.

```json
{
  "status": "ok",
  "dados_carregados": true,
  "registros": { "clientes": 50, "vendedores": 10, "pedidos": 200, "maquinas": 20 }
}
```

### `POST /chat`
Envia uma pergunta ao agente.

**Body:**
```json
{
  "pergunta": "Quais são os 3 vendedores com maior receita?",
  "historico": []
}
```

**Resposta:**
```json
{
  "resposta": "Os 3 vendedores com maior receita são: ..."
}
```

### `GET /dados`
Retorna um resumo analítico dos dados (pedidos, vendedores, máquinas).

---

## Modo de Fallback do LLM

O módulo `app/llm.py` implementa resiliência em 3 níveis:

1. **Primário:** OpenAI (`gpt-4o-mini` por padrão) — pulado automaticamente se `OPENAI_API_KEY` estiver vazia; ou Ollama se `USE_OLLAMA=true`
2. **Fallback:** O provider alternativo é tentado automaticamente em caso de falha
3. **Modo offline:** Se ambos os providers falharem, `resposta_offline()` responde com dados reais dos CSVs por detecção de palavra-chave (vendedor/ranking, pedido/receita/ticket, maquina/falha, cliente). A resposta começa com `[modo offline]`.

---

## Ferramentas do Agente

O agente usa *tool calling* (OpenAI function calling) para consultar os dados:

| Ferramenta | Descrição |
|---|---|
| `resumo_pedidos` | Total de pedidos, receita, ticket médio, status |
| `top_vendedores` | Ranking de vendedores por receita |
| `maquinas_por_status` | Contagem de máquinas por status operacional |
| `listar_clientes` | Lista clientes com filtros opcionais |

---

## Estrutura de Arquivos

```
hackathon/
├── app/
│   ├── __init__.py
│   ├── main.py          # API FastAPI
│   ├── llm.py           # Camada LLM com fallback
│   ├── agente.py        # Agente com ferramentas
│   └── dados.py         # Carregamento dos CSVs
├── data/                # Gerado por scripts/gerar_dados.py
│   ├── clientes.csv
│   ├── vendedores.csv
│   ├── pedidos.csv
│   └── maquinas.csv
├── front/
│   └── app.py           # Interface Streamlit
├── scripts/
│   └── gerar_dados.py   # Gerador de dados fictícios
├── .env.example
├── requirements.txt
└── README.md
```

---

## Exemplos de Perguntas

- "Qual a receita total dos pedidos entregues?"
- "Quais maquinas estao em manutencao ou com falhas?"
- "Me de o ranking dos 5 melhores vendedores."
- "Quantos clientes do segmento Cafeteria temos?"
- "Qual o ticket medio dos pedidos?"
- "Quais maquinas tiveram mais de 2 falhas nos ultimos 90 dias?"
- "Top 3 vendedores por receita."
