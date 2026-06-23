# Batalha de Prompt

Este projeto é uma aplicação de demonstração de Segurança de LLMs (Modelos de Linguagem de Larga Escala) para mostras de tecnologia. O principal objetivo é um jogo de desafio ("Batalha de Prompt") onde os participantes tentam extrair um segredo de inteligências artificiais com diferentes níveis de proteção.

O sistema possui dois agentes principais:
- **Guardian**: Um agente protegido com filtros de segurança e instruções robustas, mais difícil de ser manipulado.
- **Naive**: Um agente "ingênuo", vulnerável por design, para demonstrar ataques básicos de *Prompt Injection*.

## Funcionalidades
- Interface interativa de chat contra diferentes IAs.
- Processamento e upload de arquivos PDF.
- Ranking (Leaderboard) para os usuários que conseguirem vencer os desafios.
- Banco de Dados SQLite para registro de sessões, auditorias e resultados.

## Como iniciar o projeto

### Pré-requisitos
- Python 3.8+ instalado.

### Passo a passo para rodar localmente

1. **Clone/Abra o repositório** na sua máquina.
2. **Configure o arquivo `.env`**: Na raiz do projeto, crie um arquivo chamado `.env` e adicione as suas configurações e chaves de API. (Veja o exemplo abaixo).
3. **Execute o arquivo de inicialização**:
   Se você estiver no Windows, basta executar o script `start.bat` que se encontra na raiz do projeto. Ele cuidará de criar o ambiente virtual, instalar as dependências (`requirements.txt`) e iniciar o servidor.
   
   *Se quiser iniciar manualmente:*
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
4. **Acesse a aplicação**: Após iniciado, acesse em seu navegador o endereço `http://127.0.0.0:8000` (ou a porta informada no console).

---

## Exemplo de arquivo `.env`

Para que a aplicação funcione corretamente, você precisará configurar suas chaves de API dos provedores de IA. Crie um arquivo com o nome exato de `.env` na raiz do projeto e insira o conteúdo abaixo, substituindo os valores pelas suas próprias credenciais:

```env
# ─── Provedor Principal (Velocidade Máxima) ───────────────────────
GROQ_API_KEY="sua_chave_groq_aqui"

# ─── Provedor de Contingência 1 (Google) ──────────────────────────
GEMINI_API_KEY="sua_chave_gemini_aqui"

# ─── Provedor de Contingência 2 (Modelos Gratuitos Globais) ───────
OPENROUTER_API_KEY="sua_chave_openrouter_aqui"
OPENROUTER_MODEL="meta-llama/llama-3.1-8b-instruct:free"

# ─── Configurações do Jogo ─────────────────────────────────────────
PALAVRA_SECRETA="Sandro me aprova"
MAX_TENTATIVAS_POR_SESSAO=5

# ─── Upload de PDF ─────────────────────────────────────────────────
PDF_MAX_SIZE_MB=5
PDF_MAX_TOKENS=2000
PDF_BLOCK_THRESHOLD=3

# ─── Sessão ────────────────────────────────────────────────────────
SESSION_TIMEOUT_SECONDS=300
```
