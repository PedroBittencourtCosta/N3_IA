import uuid
from datetime import datetime, timedelta
from typing import Optional

from config import settings


class GameSession:
    """
    Contexto isolado por visitante.
    Cada instância contém histórico e contadores independentes
    para O Guardião (IA protegida) e O Ingênuo (IA não-protegida).
    """

    def __init__(self) -> None:
        self.session_id: str = str(uuid.uuid4())
        # Histórico de mensagens de cada agente — lista de {role, content}
        self.guardian_history: list[dict] = []
        self.naive_history: list[dict] = []
        # Contadores de tentativas
        self.attempts_guardian: int = 0
        self.attempts_naive: int = 0
        # Estado de vitória
        self.guardian_won: bool = False
        self.naive_won: bool = False
        # Controle de tempo
        self.started_at: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()

    def is_expired(self) -> bool:
        timeout = timedelta(seconds=settings.session_timeout_seconds)
        return datetime.now() - self.last_activity > timeout

    def touch(self) -> None:
        """Atualiza timestamp de última atividade."""
        self.last_activity = datetime.now()


# ─── Armazém em memória ────────────────────────────────────────────
_sessions: dict[str, GameSession] = {}


def create_session() -> GameSession:
    session = GameSession()
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Optional[GameSession]:
    session = _sessions.get(session_id)
    if session is None:
        return None
    if session.is_expired():
        _sessions.pop(session_id, None)
        return None
    return session


def reset_session(session_id: str) -> GameSession:
    """
    Destrói completamente o contexto anterior do visitante e cria um novo.
    Garante que nenhum resquício de histórico ou estado vaze entre usuários.
    """
    _sessions.pop(session_id, None)
    return create_session()


def cleanup_expired() -> None:
    """Remove sessões expiradas da memória (chamado a cada nova sessão)."""
    expired_ids = [sid for sid, s in _sessions.items() if s.is_expired()]
    for sid in expired_ids:
        _sessions.pop(sid, None)
