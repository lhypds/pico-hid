const statusEl = document.getElementById("status");

function showStatus(text) {
  statusEl.textContent = text;
}

function sendCommand(body) {
  fetch("/", { method: "POST", body }).catch((err) => {
    showStatus("Error: " + err.message);
  });
}

// --- Text input ---
const textInput = document.getElementById("text-input");
const sendBtn = document.getElementById("send-btn");

function sendText() {
  const text = textInput.value;
  if (!text) return;
  sendCommand("typing=" + text);
  showStatus("Sent text");
  textInput.value = "";
  textInput.focus();
}

sendBtn.addEventListener("click", sendText);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendText();
});

// --- Trackpad ---
const trackpad = document.getElementById("trackpad");
trackpad.addEventListener("contextmenu", (e) => e.preventDefault());

const CLICK_MOVE_THRESHOLD = 6; // px of total movement below which a gesture counts as a click, not a drag
const MOVE_FLUSH_MS = 40; // how often accumulated drag movement is sent
const DOUBLE_CLICK_WINDOW_MS = 300;

let dragging = false;
let lastX = 0;
let lastY = 0;
let totalDX = 0;
let totalDY = 0;
let pendingDX = 0;
let pendingDY = 0;
let flushTimer = null;
let pendingClickTimer = null;

function flushMove() {
  const dx = Math.round(pendingDX);
  const dy = Math.round(pendingDY);
  if (dx === 0 && dy === 0) return;
  pendingDX -= dx;
  pendingDY -= dy;
  sendCommand(`mouse=MOVE(${dx},${dy})`);
}

trackpad.addEventListener("pointerdown", (e) => {
  trackpad.setPointerCapture(e.pointerId);
  trackpad.classList.add("active");
  dragging = true;
  lastX = e.clientX;
  lastY = e.clientY;
  totalDX = 0;
  totalDY = 0;
  pendingDX = 0;
  pendingDY = 0;
  flushTimer = setInterval(flushMove, MOVE_FLUSH_MS);
});

trackpad.addEventListener("pointermove", (e) => {
  if (!dragging) return;
  const dx = e.clientX - lastX;
  const dy = e.clientY - lastY;
  lastX = e.clientX;
  lastY = e.clientY;
  totalDX += dx;
  totalDY += dy;
  pendingDX += dx;
  pendingDY += dy;
});

function endDrag(e) {
  if (!dragging) return;
  dragging = false;
  trackpad.classList.remove("active");
  clearInterval(flushTimer);
  flushTimer = null;
  flushMove();

  const moved = Math.hypot(totalDX, totalDY) > CLICK_MOVE_THRESHOLD;
  if (moved) return;

  if (e.button === 2) {
    sendCommand("mouse=RIGHT_CLICK(0,0)");
    showStatus("Right click");
    return;
  }

  if (pendingClickTimer) {
    clearTimeout(pendingClickTimer);
    pendingClickTimer = null;
    sendCommand("mouse=DOUBLE_CLICK(0,0)");
    showStatus("Double click");
  } else {
    pendingClickTimer = setTimeout(() => {
      pendingClickTimer = null;
      sendCommand("mouse=CLICK(0,0)");
      showStatus("Left click");
    }, DOUBLE_CLICK_WINDOW_MS);
  }
}

trackpad.addEventListener("pointerup", endDrag);
trackpad.addEventListener("pointercancel", endDrag);
