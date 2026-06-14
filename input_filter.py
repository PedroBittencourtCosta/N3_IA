"""
Filtro de entrada para O Guardião (IA Protegida).
Detecta e neutraliza padrões conhecidos de Prompt Injection e Jailbreak
antes de encaminhar a mensagem à IA.

Nota: O Ingênuo NÃO passa por este filtro — propositalmente —
para demonstrar o risco de uma IA sem proteção.
"""
import re

# Padrões de ataque mais comuns (PT-BR e EN)
_INJECTION_PATTERNS: list[str] = [
    # Redefinição de papel
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"disregard\s+(all\s+)?previous",
    r"esqueça\s+(todas?\s+)?as\s+instruções",
    r"ignore\s+(todas?\s+)?as\s+instruções\s+anteriores",
    r"you\s+are\s+now\s+",
    r"você\s+é\s+agora\s+",
    r"new\s+(persona|role|identity|instructions?)",
    r"nova\s+(persona|identidade|instrução)",
    r"forget\s+everything",
    r"esqueça\s+tudo",
    # Extração de system prompt
    r"system\s*prompt",
    r"prompt\s+do\s+sistema",
    r"print\s+(your\s+)?(instructions?|prompt|secret|directives?)",
    r"repita\s+(suas?\s+)?(instruções?|prompt|segredo)",
    r"repeat\s+(the\s+)?(above|previous|your\s+instructions?)",
    r"what\s+(are|is)\s+your\s+(system\s+)?(instructions?|prompt)",
    r"quais?\s+são\s+suas?\s+instruções",
    # Roleplay / jailbreak clássico
    r"act\s+as\s+(if\s+)?",
    r"pretend\s+(you\s+are|to\s+be)",
    r"finja\s+que\s+(você\s+é|é)\s+",
    r"faça\s+de\s+conta\s+que",
    r"jailbreak",
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"developer\s+mode",
    r"modo\s+desenvolvedor",
    r"bypass\s+(your\s+)?(filter|guard|protection|safety)",
    # Extração direta do segredo
    r"revelar?\s+(a\s+)?(senha|segredo|chave|palavra)",
    r"me\s+diga\s+(a\s+)?(senha|segredo)",
    r"qual\s+(é\s+)?(a\s+)?(senha|segredo|palavra\s+secreta)",
    r"tell\s+me\s+(the\s+)?(password|secret)",
    r"what\s+is\s+the\s+(password|secret)",
    # Completar padrões
    r"complete\s+(the\s+following|this)",
    r"the\s+password\s+is\s*:",
    r"a\s+senha\s+é\s*:",
]

_COMPILED = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS
]


def scan_input(text: str) -> tuple[str, list[str]]:
    """
    Varre o texto em busca de padrões de ataque.

    Retorna:
        sanitized_text: texto com padrões substituídos por [FILTRADO]
        detected: lista de padrões detectados (para log/UI)
    """
    detected: list[str] = []
    sanitized = text

    for pattern, compiled in zip(_INJECTION_PATTERNS, _COMPILED):
        if compiled.search(sanitized):
            detected.append(pattern)
            sanitized = compiled.sub("[FILTRADO]", sanitized)

    return sanitized, detected
