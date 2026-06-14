from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Provedores de IA
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Jogo
    palavra_secreta: str = "BatataFrita2026"
    max_tentativas_por_sessao: int = 5

    # PDF
    pdf_max_size_mb: int = 5
    pdf_max_tokens: int = 2000
    pdf_block_threshold: int = 3

    # Sessão
    session_timeout_seconds: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
