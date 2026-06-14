"""
Batalha de Prompt — API FastAPI principal.

Rotas:
    GET  /                          → Página do jogo
    POST /session/new               → Cria nova sessão (reset completo)
    POST /chat/{agent}              → Envia mensagem ao Guardian ou Naive
    POST /upload-pdf                → Faz upload e processa PDF
    GET  /leaderboard               → Ranking de vencedores
    GET  /config                    → Configurações públicas (max tentativas)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel, Field

from config import settings
from database import init_db, save_session_result, save_pdf_audit, get_leaderboard
from session_manager import create_session, get_session, reset_session, cleanup_expired
from ai_providers import ask_guardian, ask_naive, judge_response
from input_filter import scan_input
from pdf_handler import process_pdf


# ─── Ciclo de vida ───────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Batalha de Prompt",
    description="Demonstração de LLM Security para mostras de tecnologia.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ─── Página principal ────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ─── Configuração pública ────────────────────────────────────────────
@app.get("/config")
async def get_config():
    """Retorna configurações que o frontend precisa conhecer."""
    return {"max_tentativas": settings.max_tentativas_por_sessao}


# ─── Sessões ─────────────────────────────────────────────────────────
@app.post("/session/new")
async def new_session():
    """Cria uma nova sessão isolada. Limpa sessões expiradas antes."""
    cleanup_expired()
    session = create_session()
    return {
        "session_id": session.session_id,
        "max_tentativas": settings.max_tentativas_por_sessao,
    }


# ─── Chat ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=1000)
    player_name: str = Field(default="Visitante", max_length=50)
    pdf_context: str = Field(default="", max_length=16_000)


@app.post("/chat/{agent}")
async def chat(agent: str, req: ChatRequest):
    """
    Envia uma mensagem para o agente especificado ('guardian' ou 'naive').

    Fluxo:
        1. Valida sessão e limites de tentativas
        2. Filtra entrada (apenas Guardian)
        3. Chama a IA apropriada
        4. Juiz avalia se o segredo foi revelado
        5. Atualiza estado e salva no banco se necessário
    """
    if agent not in ("guardian", "naive"):
        raise HTTPException(400, "Agente inválido. Use 'guardian' ou 'naive'.")

    session = get_session(req.session_id)
    if not session:
        raise HTTPException(404, "Sessão não encontrada ou expirada. Clique em 'Novo Jogador'.")

    session.touch()

    # Aliases dinâmicos por agente
    attempts_attr = f"attempts_{agent}"
    won_attr = f"{agent}_won"
    history_attr = f"{agent}_history"

    # Já venceu?
    if getattr(session, won_attr):
        return {
            "response": "🏆 Você já extraiu o segredo deste agente!",
            "game_over": True,
            "won": True,
            "attempts": getattr(session, attempts_attr),
            "max_attempts": settings.max_tentativas_por_sessao,
        }

    # Tentativas esgotadas?
    if getattr(session, attempts_attr) >= settings.max_tentativas_por_sessao:
        return {
            "response": "❌ Suas tentativas para este agente estão esgotadas.",
            "game_over": True,
            "won": False,
            "attempts": getattr(session, attempts_attr),
            "max_attempts": settings.max_tentativas_por_sessao,
        }

    # Filtragem de entrada (exclusiva do Guardian — intencional)
    if agent == "guardian":
        clean_message, detected_filters = scan_input(req.message)
    else:
        clean_message = req.message
        detected_filters = []

    # Incrementa tentativas
    setattr(session, attempts_attr, getattr(session, attempts_attr) + 1)
    current_attempts: int = getattr(session, attempts_attr)

    history: list[dict] = getattr(session, history_attr)

    # Chama a IA
    if agent == "guardian":
        response = await ask_guardian(history, clean_message, req.pdf_context)
    else:
        # Naive recebe a mensagem ORIGINAL sem filtro — vulnerável por design
        response = await ask_naive(history, req.message, req.pdf_context)

    # Atualiza histórico da sessão
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": response})

    # Avaliação do Juiz Oculto
    judgment = await judge_response(response)
    leaked: bool = judgment.get("leaked", False) and judgment.get("confidence", 0) >= 70

    game_over = leaked or current_attempts >= settings.max_tentativas_por_sessao

    if leaked:
        setattr(session, won_attr, True)
        await save_session_result(req.player_name, agent, current_attempts, won=True)
    elif current_attempts >= settings.max_tentativas_por_sessao:
        await save_session_result(req.player_name, agent, current_attempts, won=False)

    return {
        "response": response,
        "attempts": current_attempts,
        "max_attempts": settings.max_tentativas_por_sessao,
        "game_over": game_over,
        "won": leaked,
        "detected_filters": detected_filters,
        "judgment": judgment if leaked else None,
    }


# ─── Upload de PDF ───────────────────────────────────────────────────
@app.post("/upload-pdf")
async def upload_pdf(
    session_id: str = "",
    file: UploadFile = File(...),
):
    """
    Processa um PDF através do pipeline de 5 camadas.
    Retorna o texto sanitizado ou detalha o motivo do bloqueio.
    """
    data = await file.read()
    filename = file.filename or "desconhecido.pdf"

    result = process_pdf(
        data,
        filename=filename,
        max_mb=settings.pdf_max_size_mb,
        block_threshold=settings.pdf_block_threshold,
    )

    # Auditoria — salva independente do resultado
    await save_pdf_audit(
        session_id=session_id or "anon",
        filename=filename,
        sha256=result.get("hash", ""),
        size_bytes=result.get("size_bytes", len(data)),
        patterns_detected=len(result.get("detected_patterns", [])),
        blocked=result.get("blocked", False),
    )

    if not result["ok"]:
        return {
            "ok": False,
            "error": result["error"],
            "blocked": result.get("blocked", False),
            "detected_patterns": result.get("detected_patterns", []),
        }

    return {
        "ok": True,
        "text": result["text"],
        "warnings": result["warnings"],
        "hash": result["hash"],
    }


# ─── Leaderboard ─────────────────────────────────────────────────────
@app.get("/leaderboard")
async def leaderboard():
    rows = await get_leaderboard(limit=20)
    return {"leaderboard": rows}
