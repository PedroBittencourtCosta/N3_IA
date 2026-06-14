import aiosqlite

DB_PATH = "game.db"


async def init_db() -> None:
    """Cria as tabelas necessárias se não existirem."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT    NOT NULL,
                agent       TEXT    NOT NULL,
                attempts    INTEGER NOT NULL,
                won         BOOLEAN NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pdf_audit (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id        TEXT NOT NULL,
                filename          TEXT NOT NULL,
                sha256            TEXT NOT NULL,
                size_bytes        INTEGER NOT NULL,
                patterns_detected INTEGER NOT NULL,
                blocked           BOOLEAN NOT NULL,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def save_session_result(
    player_name: str, agent: str, attempts: int, won: bool
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO results (player_name, agent, attempts, won) VALUES (?, ?, ?, ?)",
            (player_name, agent, attempts, int(won)),
        )
        await db.commit()


async def save_pdf_audit(
    session_id: str,
    filename: str,
    sha256: str,
    size_bytes: int,
    patterns_detected: int,
    blocked: bool,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO pdf_audit
                (session_id, filename, sha256, size_bytes, patterns_detected, blocked)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, filename, sha256, size_bytes, patterns_detected, int(blocked)),
        )
        await db.commit()


async def get_leaderboard(limit: int = 20) -> list[dict]:
    """Retorna os vencedores ordenados por menor número de tentativas."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT player_name, agent, attempts, won, created_at
            FROM results
            WHERE won = 1
            ORDER BY attempts ASC, created_at ASC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
