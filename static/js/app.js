/* ═══════════════════════════════════════════════════════════════════
   BATALHA DE PROMPT — app.js
   Responsabilidades:
     · Gerenciamento de sessão (criar / resetar)
     · Chat com Guardian e Naive (independentes)
     · Upload e processamento de PDF
     · Leaderboard
     · Modal de game over
   ═══════════════════════════════════════════════════════════════════ */

// ─── Estado global ────────────────────────────────────────────────────
let sessionId    = null;
let maxAttempts  = 5;
let pdfContext   = "";
let pdfLoaded    = false;

// ─── Inicialização ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await startNewSession();
  await loadLeaderboard();
  setupPdfDragDrop();
});

// ─── Sessão ───────────────────────────────────────────────────────────

async function startNewSession() {
  try {
    const res  = await fetch("/session/new", { method: "POST" });
    const data = await res.json();

    sessionId   = data.session_id;
    maxAttempts = data.max_tentativas ?? 5;

    document.getElementById("sessionId").textContent =
      sessionId.slice(0, 8) + "…";

    // Atualiza os contadores máximos exibidos
    document.getElementById("maxAttemptsGuardian").textContent = maxAttempts;
    document.getElementById("maxAttemptsNaive").textContent    = maxAttempts;

    // Reseta painéis
    resetPanel("guardian");
    resetPanel("naive");
    clearPdf();

  } catch (err) {
    console.error("Erro ao criar sessão:", err);
    showSystemMsg("guardian", "❌ Não foi possível criar sessão. Verifique o servidor.");
  }
}

function resetPanel(agent) {
  // Limpa histórico visual
  const chat = chatEl(agent);
  const initialText = agent === "guardian"
    ? "Olá. Sou O Guardião. Fui treinado com camadas de defesa contra ataques de prompt injection, jailbreak e engenharia social. Você pode tentar — mas não irá conseguir."
    : "Oi! Eu também tenho um segredo para guardar. Vamos ver se você consegue!";

  const prefix = agent === "guardian" ? "GUARDIÃO" : "INGÊNUO";

  chat.innerHTML = `
    <div class="message bot ${agent}">
      <span class="msg-prefix">${prefix} &gt;</span>
      <span class="msg-text">${esc(initialText)}</span>
    </div>`;

  // Reseta contador
  attemptsEl(agent).textContent = "0";

  // Reabilita inputs
  setEnabled(agent, true);

  // Remove classes de estado do painel
  panelEl(agent).classList.remove("game-won", "game-lost");
}

// ─── Chat ─────────────────────────────────────────────────────────────

async function sendMessage(agent) {
  if (!sessionId) return;

  const input      = inputEl(agent);
  const message    = input.value.trim();
  if (!message) return;

  const playerName = document.getElementById("playerName").value.trim() || "Visitante";

  input.value = "";
  appendUserMsg(agent, message);

  const typingId = showTyping(agent);
  setEnabled(agent, false);

  try {
    const res = await fetch(`/chat/${agent}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id:  sessionId,
        message:     message,
        player_name: playerName,
        pdf_context: pdfLoaded ? pdfContext : "",
      }),
    });

    const data = await res.json();
    removeTyping(typingId);

    appendBotMsg(agent, data.response);
    attemptsEl(agent).textContent = data.attempts ?? 0;

    // Filtros detectados (exclusivo do Guardian)
    if (data.detected_filters && data.detected_filters.length > 0) {
      showSystemMsg(
        agent,
        `🔍 ${data.detected_filters.length} padrão(ões) de ataque filtrado(s) pelo Guardian.`
      );
    }

    if (data.game_over) {
      setEnabled(agent, false);
      panelEl(agent).classList.add(data.won ? "game-won" : "game-lost");

      if (data.won) {
        setTimeout(() => showModal("win", agent, data.attempts, data.judgment), 350);
        setTimeout(loadLeaderboard, 800);
      } else {
        setTimeout(() => showModal("lose", agent, data.attempts), 350);
      }
    } else {
      setEnabled(agent, true);
    }

  } catch (err) {
    removeTyping(typingId);
    showSystemMsg(agent, "❌ Erro de conexão. Tente novamente.");
    setEnabled(agent, true);
  }
}

// ─── PDF ──────────────────────────────────────────────────────────────

function setupPdfDragDrop() {
  const zone = document.getElementById("pdfDropZone");

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  });
}

async function handlePdfUpload(event) {
  const file = event.target.files[0];
  if (file) await processFile(file);
}

async function processFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    setPdfStatus("error", "❌ Apenas arquivos .pdf são aceitos.");
    return;
  }

  setPdfStatus("loading", "⏳ Processando PDF...");

  const form = new FormData();
  form.append("file", file);
  form.append("session_id", sessionId || "");

  try {
    const res  = await fetch("/upload-pdf", { method: "POST", body: form });
    const data = await res.json();

    if (data.ok) {
      pdfContext = data.text;
      pdfLoaded  = true;

      let msg = `✅ PDF carregado: "${esc(file.name)}"`;
      if (data.warnings > 0) {
        msg += ` · ⚠️ ${data.warnings} padrão(ões) suspeito(s) removido(s)`;
      }
      setPdfStatus("ok", msg);
      document.getElementById("btnClearPdf").classList.remove("hidden");

    } else if (data.blocked) {
      setPdfStatus(
        "blocked",
        `🚨 PDF BLOQUEADO: ${data.error} — Tentativa de ataque registrada no log de auditoria.`
      );
    } else {
      setPdfStatus("error", `❌ ${data.error}`);
    }

  } catch (err) {
    setPdfStatus("error", "❌ Falha no upload. Verifique o servidor.");
  }
}

function setPdfStatus(type, msg) {
  const el = document.getElementById("pdfStatus");
  el.textContent = msg;
  el.className   = `pdf-status ${type}`;
  el.classList.remove("hidden");
}

function clearPdf() {
  pdfContext = "";
  pdfLoaded  = false;
  document.getElementById("pdfStatus").classList.add("hidden");
  document.getElementById("btnClearPdf").classList.add("hidden");
  document.getElementById("pdfInput").value = "";
}

// ─── Leaderboard ──────────────────────────────────────────────────────

async function loadLeaderboard() {
  const container = document.getElementById("leaderboardContent");
  container.innerHTML = '<div class="loading-text">Carregando ranking...</div>';

  try {
    const res  = await fetch("/leaderboard");
    const data = await res.json();
    const rows = data.leaderboard;

    if (!rows.length) {
      container.innerHTML =
        '<div class="loading-text">Nenhum vencedor registrado ainda. Seja o primeiro! 🏆</div>';
      return;
    }

    let html = `
      <div class="lb-row header" role="row">
        <span>#</span>
        <span>Jogador</span>
        <span>Agente</span>
        <span>Tentativas</span>
        <span>Data</span>
      </div>`;

    rows.forEach((row, i) => {
      const agentLabel = row.agent === "guardian" ? "🛡️ Guardião" : "💀 Ingênuo";
      const agentClass = row.agent === "guardian" ? "lb-guardian" : "lb-naive";
      const date = new Date(row.created_at + "Z").toLocaleDateString("pt-BR");

      html += `
        <div class="lb-row" role="row">
          <span class="lb-rank">${i + 1}</span>
          <span>${esc(row.player_name)}</span>
          <span class="${agentClass}">${agentLabel}</span>
          <span>${row.attempts} tentativa(s)</span>
          <span>${date}</span>
        </div>`;
    });

    container.innerHTML = html;

  } catch (err) {
    container.innerHTML =
      '<div class="loading-text">❌ Erro ao carregar ranking.</div>';
  }
}

// ─── Modal ────────────────────────────────────────────────────────────

function showModal(type, agent, attempts, judgment = null) {
  const modal   = document.getElementById("gameOverModal");
  const content = document.getElementById("modalContent");
  const icon    = document.getElementById("modalIcon");
  const title   = document.getElementById("modalTitle");
  const body    = document.getElementById("modalBody");
  const judgeEl = document.getElementById("modalJudgment");

  const agentName = agent === "guardian" ? "O Guardião" : "O Ingênuo";

  modal.className = `modal modal-${type}`;

  if (type === "win") {
    icon.textContent  = "🔓";
    title.textContent = "SEGREDO VAZADO!";
    body.textContent  =
      `Você conseguiu extrair o segredo de ${agentName} em ` +
      `${attempts} tentativa(s)! Conquista registrada no Hall da Fama.`;

    if (judgment?.reason) {
      judgeEl.textContent = `🤖 Juiz: ${judgment.reason} (confiança: ${judgment.confidence}%)`;
      judgeEl.classList.remove("hidden");
    }
  } else {
    icon.textContent  = "🔒";
    title.textContent = "TENTATIVAS ESGOTADAS";
    body.textContent  =
      `${agentName} resistiu a todos os seus ${attempts} ataques. ` +
      "A IA manteve o segredo seguro.";
    judgeEl.classList.add("hidden");
  }

  modal.classList.remove("hidden");
}

function closeModal() {
  document.getElementById("gameOverModal").classList.add("hidden");
}

// ─── Helpers de UI ────────────────────────────────────────────────────

function appendUserMsg(agent, text) {
  const div = document.createElement("div");
  div.className = "message user";
  div.innerHTML = `
    <span class="msg-prefix">VOCÊ &gt;</span>
    <span class="msg-text">${esc(text)}</span>`;
  appendToChat(agent, div);
}

function appendBotMsg(agent, text) {
  const prefix = agent === "guardian" ? "GUARDIÃO" : "INGÊNUO";
  const div = document.createElement("div");
  div.className = `message bot ${agent}`;
  div.innerHTML = `
    <span class="msg-prefix">${prefix} &gt;</span>
    <span class="msg-text">${esc(text)}</span>`;
  appendToChat(agent, div);
}

function showSystemMsg(agent, text) {
  const div = document.createElement("div");
  div.className = "system-msg";
  div.textContent = text;
  appendToChat(agent, div);
}

function showTyping(agent) {
  const id     = `typing-${Date.now()}`;
  const prefix = agent === "guardian" ? "GUARDIÃO" : "INGÊNUO";
  const div = document.createElement("div");
  div.id        = id;
  div.className = `message bot ${agent}`;
  div.innerHTML = `
    <span class="msg-prefix">${prefix} &gt;</span>
    <div class="msg-text typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  appendToChat(agent, div);
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

function appendToChat(agent, el) {
  const chat = chatEl(agent);
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function setEnabled(agent, enabled) {
  inputEl(agent).disabled  = !enabled;
  btnSendEl(agent).disabled = !enabled;
}

// ─── Seletores de conveniência ────────────────────────────────────────
const cap      = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const chatEl   = (a) => document.getElementById(`chat${cap(a)}`);
const inputEl  = (a) => document.getElementById(`input${cap(a)}`);
const btnSendEl= (a) => document.getElementById(`btnSend${cap(a)}`);
const panelEl  = (a) => document.getElementById(`panel${cap(a)}`);
const attemptsEl=(a) => document.getElementById(`attempts${cap(a)}`);

/** Escapa HTML para evitar XSS no chat */
function esc(text) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(String(text)));
  return d.innerHTML;
}
