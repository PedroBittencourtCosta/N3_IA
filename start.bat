@echo off
echo.
echo  ======================================================
echo   BATALHA DE PROMPT — LLM Security Demo
echo  ======================================================
echo.

REM Verifica se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale o Python 3.11+.
    pause
    exit /b 1
)

REM Verifica se as dependencias estao instaladas
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando dependencias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias.
        pause
        exit /b 1
    )
)

REM Copia .env.example para .env se nao existir
if not exist ".env" (
    echo [INFO] Criando .env a partir do .env.example...
    copy .env.example .env
    echo [ATENCAO] Edite o arquivo .env com suas chaves de API antes de continuar!
    notepad .env
)

echo [OK] Iniciando servidor...
echo [OK] Acesse: http://localhost:8000
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
