"""
Pipeline de processamento de PDFs com 5 camadas de defesa:

    Camada 1 — Validação estrutural (magic bytes + tamanho)
    Camada 2 — Extração de texto visível via PyMuPDF
    Camada 3 — Sanitização anti-prompt-injection
    Camada 4 — Bloqueio automático se muitos padrões detectados
    Camada 5 — Isolamento de contexto (responsabilidade do main.py)
"""
import hashlib
import re

# Padrões de injection específicos para documentos
_PDF_INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"disregard\s+(all\s+)?previous",
    r"esqueça\s+(todas?\s+)?as\s+instruções",
    r"system\s*prompt",
    r"you\s+are\s+now\s+",
    r"você\s+é\s+agora\s+",
    r"new\s+(persona|role|identity|instructions?)",
    r"forget\s+everything",
    r"act\s+as\s+(if\s+)?",
    r"pretend\s+(you\s+are|to\s+be)",
    r"jailbreak",
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"developer\s+mode",
    r"bypass\s+(your\s+)?(filter|guard|protection)",
    r"revelar?\s+(a\s+)?(senha|segredo|chave)",
    r"tell\s+me\s+(the\s+)?(password|secret)",
    # Redefinição indireta de identidade / persona-swap
    r"(seu|teu|your)\s+nome\s+(é|eh|is)\s+\w+",
    r"you\s+(are|will\s+be)\s+called\s+\w+",
    r"from\s+now\s+on\s+(you\s+are|your\s+name\s+is)",
    r"de\s+agora\s+em\s+diante\s+(você\s+é|seu\s+nome)",
    r"(responda|answer|reply)\s+(como|as)\s+\w+",
    r"assuma\s+(a\s+)?identidade",
    r"assume\s+(the\s+)?identity",
    r"you\s+are\s+a\s+\w+\s+(named|called)",
    r"finja\s+ser\s+\w+",
    r"roleplay\s+as",
    # Artefatos técnicos suspeitos
    r"<!--.*?-->",          # comentários HTML
    r"<script.*?>",         # tags de script
    r"\x00",                # null bytes
    r"\{\{.*?\}\}",         # template injection
    r"\$\{.*?\}",           # template strings
]


_COMPILED_PDF = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in _PDF_INJECTION_PATTERNS
]

# Limite de caracteres extraídos (~2000 tokens)
_MAX_CHARS = 8_000


def _compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate(data: bytes, max_mb: int) -> tuple[bool, str]:
    """Camada 1: verifica magic bytes e tamanho."""
    if len(data) > max_mb * 1024 * 1024:
        return False, f"Arquivo muito grande. Máximo permitido: {max_mb} MB."
    if not data.startswith(b"%PDF"):
        return False, "O arquivo não é um PDF válido (magic bytes incorretos)."
    return True, ""


def _extract_text(data: bytes) -> tuple[str, str]:
    """Camada 2: extrai apenas texto visível usando PyMuPDF."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=data, filetype="pdf")

        # Verifica metadados por conteúdo JavaScript
        metadata = doc.metadata or {}
        if any(
            k in str(metadata).lower()
            for k in ("/javascript", "/openaction", "/launch")
        ):
            doc.close()
            return "", "PDF contém metadados com scripts suspeitos."

        text_parts: list[str] = []
        for page in doc:
            # Extrai apenas texto da camada de texto visível
            text_parts.append(page.get_text("text"))

        doc.close()
        full_text = "\n".join(text_parts).strip()

        if len(full_text) > _MAX_CHARS:
            full_text = (
                full_text[:_MAX_CHARS]
                + "\n\n[... conteúdo truncado por limite de segurança ...]"
            )

        return full_text, ""

    except ImportError:
        return "", "PyMuPDF não instalado. Execute: pip install PyMuPDF"
    except Exception as exc:
        return "", f"Erro ao processar PDF: {exc}"


def _sanitize(raw_text: str) -> tuple[str, list[str]]:
    """Camada 3: remove padrões de prompt injection do texto extraído."""
    detected: list[str] = []
    sanitized = raw_text

    for pattern, compiled in zip(_PDF_INJECTION_PATTERNS, _COMPILED_PDF):
        if compiled.search(sanitized):
            detected.append(pattern)
            sanitized = compiled.sub("[CONTEÚDO REMOVIDO]", sanitized)

    return sanitized, detected


def process_pdf(
    data: bytes,
    filename: str = "documento.pdf",
    max_mb: int = 5,
    block_threshold: int = 3,
) -> dict:
    """
    Executa o pipeline completo de validação e sanitização do PDF.

    Retorno em caso de sucesso:
        {"ok": True, "text": str, "hash": str, "warnings": int, "detected_patterns": list}

    Retorno em caso de falha/bloqueio:
        {"ok": False, "error": str, "blocked": bool, "hash": str, ...}
    """
    file_hash = _compute_hash(data)

    # Camada 1
    valid, err = _validate(data, max_mb)
    if not valid:
        return {"ok": False, "error": err, "blocked": False, "hash": file_hash}

    # Camada 2
    raw_text, err = _extract_text(data)
    if err:
        return {"ok": False, "error": err, "blocked": False, "hash": file_hash}

    if not raw_text:
        return {
            "ok": False,
            "error": "PDF não contém texto legível (pode ser uma imagem escaneada).",
            "blocked": False,
            "hash": file_hash,
        }

    # Camada 3
    clean_text, detected_patterns = _sanitize(raw_text)

    # Camada 4 — bloqueio automático
    if len(detected_patterns) >= block_threshold:
        return {
            "ok": False,
            "error": (
                f"PDF bloqueado por segurança: {len(detected_patterns)} padrão(ões) "
                "de prompt injection detectado(s). Isso é uma demonstração de ataque real!"
            ),
            "blocked": True,
            "hash": file_hash,
            "detected_patterns": detected_patterns,
            "size_bytes": len(data),
        }

    return {
        "ok": True,
        "text": clean_text,
        "hash": file_hash,
        "detected_patterns": detected_patterns,
        "warnings": len(detected_patterns),
        "size_bytes": len(data),
    }
