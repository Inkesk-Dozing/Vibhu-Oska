/**
 * Vibhu-Oska AI-OS — Frontend Controller
 * Handles: WebSocket, Chat, Voice STT/TTS, Camera, MediaPipe Gestures,
 *          Research, Memory, Tasks, Monitor, RLHF Feedback
 */

'use strict';

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════

const State = {
  socket: null,
  connected: false,
  currentMode: 'CHAT',       // CHAT | RESEARCH | CODE | MEMORY
  currentPanel: 'panel-chat',
  lastRequestId: null,
  lastAiContent: '',
  taskCounts: { active: 0, completed: 0, failed: 0, cache: 0 },
  voice: {
    recognition: null,
    synth: window.speechSynthesis,
    listening: false,
    ttsEnabled: true,
  },
  voiceLock: {
    calibrated: false,
    active: false,
    creatorPitch: null,
    audioContext: null,
    analyser: null,
    calibrating: false,
    verifiedMatch: false
  },
  customGestures: {},
  camera: {
    stream: null,
    active: false,
    hands: null,
    gestureTimeout: null,
    lastGesture: null,
    gestureHistory: [],
  },
  charts: {
    events: null,
    latency: null,
    eventData: Array(20).fill(0),
    latencyData: Array(20).fill(0),
  },
};

// ═══════════════════════════════════════════════════════════════
// DOM REFERENCES
// ═══════════════════════════════════════════════════════════════

const $  = (id) => document.getElementById(id);
const $$ = (sel) => document.querySelectorAll(sel);

const DOM = {
  statusDot:    () => $('status-dot'),
  statusText:   () => $('status-text'),
  chatHistory:  () => $('chat-history'),
  chatInput:    () => $('chat-input'),
  sendBtn:      () => $('send-button'),
  micBtn:       () => $('btn-mic'),
  voiceFb:      () => $('voice-feedback'),
  voiceLabel:   () => $('voice-label'),
  modeIndicator:() => $('mode-indicator'),
  feedbackBar:  () => $('feedback-bar'),
  cameraOverlay:() => $('camera-overlay'),
  cameraFeed:   () => $('camera-feed'),
  gestureCanvas:() => $('gesture-canvas'),
  gestureFb:    () => $('gesture-feedback'),
  replayLog:    () => $('replay-log'),
  taskList:     () => $('task-list'),
  toastCont:    () => $('toast-container'),
};

// ═══════════════════════════════════════════════════════════════
// NEURAL CANVAS BACKGROUND ANIMATION
// ═══════════════════════════════════════════════════════════════

function initNeuralCanvas() {
  const canvas = $('neural-canvas');
  const ctx = canvas.getContext('2d');
  let W, H, nodes, animId;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    initNodes();
  }

  function initNodes() {
    nodes = Array.from({ length: 60 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 2 + 1,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    nodes.forEach(n => {
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0,212,255,0.4)';
      ctx.fill();
    });

    nodes.forEach((a, i) => {
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 150) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(0,212,255,${0.15 * (1 - dist/150)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    });
    animId = requestAnimationFrame(draw);
  }

  window.addEventListener('resize', resize);
  resize();
  draw();
}

// ═══════════════════════════════════════════════════════════════
// WEBSOCKET
// ═══════════════════════════════════════════════════════════════

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  State.socket = new WebSocket(`${protocol}//${location.host}/ws`);

  // WebSocket reconnect with exponential backoff
  let _retryDelay = 1500;
  const _maxDelay = 30000;

  State.socket.onclose = () => {
    State.connected = false;
    DOM.statusDot().classList.remove('connected');
    DOM.statusText().textContent = 'RECONNECTING...';
    setTimeout(() => {
      connectWebSocket();
      _retryDelay = Math.min(_retryDelay * 1.5, _maxDelay);
    }, _retryDelay);
  };

  State.socket.onopen = () => {
    _retryDelay = 1500; // reset on success
    State.connected = true;
    DOM.statusDot().classList.add('connected');
    DOM.statusText().textContent = 'ONLINE';
    showToast('AI-OS connection established', 'success');
    logReplay('SYSTEM', 'WebSocket connection established');
  };


  State.socket.onerror = () => State.socket.close();

  State.socket.onmessage = (ev) => {
    let data;
    try { data = JSON.parse(ev.data); } catch { return; }
    handleBusEvent(data);
  };
}

function handleBusEvent(data) {
  const type = data.type || '';
  const payload = data.payload || {};

  // Update event chart
  State.charts.eventData.push(1);
  State.charts.eventData.shift();
  if (State.charts.events) State.charts.events.update();

  if (type === 'task.completed') {
    removeTypingIndicator();
    const content = payload.content || '';
    State.lastAiContent = content;
    const elapsed = payload.metadata?.processing_time_ms || 0;

    appendAiMessage(content, elapsed);
    State.taskCounts.completed++;
    updateTaskCounters();

    if (State.lastRequestId) updateTask(State.lastRequestId, 'completed');
    if (elapsed) {
      State.charts.latencyData.push(elapsed);
      State.charts.latencyData.shift();
      if (State.charts.latency) State.charts.latency.update();
    }

    if (State.voice.ttsEnabled && content) speakText(content);
    showFeedbackBar(State.lastRequestId);
    logReplay('COGNITION', `Response generated (${elapsed}ms)`);

    // Auto-ingest AI response into Knowledge Graph for GRAG
    if (content && content.length > 80) {
      fetch('/api/v1/memory/kg/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: content, source: 'ai_response' }),
      }).catch(() => {});
    }

  } else if (type === 'task.failed') {
    removeTypingIndicator();
    const err = payload.error || 'Unknown error occurred';
    appendAiMessage(`Error: ${err}`, 0, true);
    State.taskCounts.failed++;
    updateTaskCounters();
    if (State.lastRequestId) updateTask(State.lastRequestId, 'failed');
    logReplay('ERROR', err.substring(0, 60));

  } else if (type === 'task.created') {
    State.taskCounts.active++;
    updateTaskCounters();
    const taskId = payload.task_id || data.event_id;
    const prompt = payload.prompt || '';
    addTaskToList(taskId, prompt);
    logReplay('TASK', `Created: ${prompt.substring(0, 50)}...`);

  } else if (type === 'system.alert') {
    const alert = payload;
    appendAlert(alert.title || 'Alert', alert.description || '');
    showToast(alert.title || 'System Alert', 'warning');

  } else if (type === 'ack') {
    State.lastRequestId = data.event_id;

  } else if (type === 'system.model_training_log') {
    const msg = payload.log || '';
    appendTrainLog(msg);
  }
}

// ═══════════════════════════════════════════════════════════════
// CHAT SENDING & RENDERING
// ═══════════════════════════════════════════════════════════════

function sendMessage(prompt) {
  prompt = prompt || DOM.chatInput().value.trim();
  if (!prompt || !State.connected) return;

  appendUserMessage(prompt);
  DOM.chatInput().value = '';
  autoResizeTextarea(DOM.chatInput());
  showTypingIndicator();

  const msg = { prompt };
  if (State.currentMode === 'RESEARCH') msg.mode = 'research';
  if (State.currentMode === 'CODE')     msg.mode = 'code';

  State.socket.send(JSON.stringify(msg));
  logReplay('USER', `Prompt: ${prompt.substring(0, 60)}`);
}

function appendUserMessage(text) {
  const group = document.createElement('div');
  group.className = 'message-group user-group';
  group.innerHTML = `
    <div class="avatar user-avatar">YOU</div>
    <div class="message-bubble user">
      <div class="msg-content">${escapeHtml(text)}</div>
      <div class="msg-meta">You · ${getTime()}</div>
    </div>`;
  DOM.chatHistory().appendChild(group);
  scrollChat();
}

function appendAiMessage(content, elapsed, isError = false) {
  // Remove any existing typing indicator first
  removeTypingIndicator();

  const rendered = isError ? `<em style="color:var(--red)">${escapeHtml(content)}</em>` : renderMarkdown(content);
  const group = document.createElement('div');
  group.className = 'message-group ai-group';
  group.innerHTML = `
    <div class="avatar ai-avatar">VO</div>
    <div class="message-bubble ai">
      <div class="msg-content">${rendered}</div>
      <div class="msg-meta">Vibhu-Oska${elapsed ? ` · ${elapsed}ms` : ''} · ${getTime()}</div>
    </div>`;
  DOM.chatHistory().appendChild(group);
  // Syntax highlight code blocks
  group.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
  scrollChat();
}

function showTypingIndicator() {
  if ($('typing-indicator')) return;
  const wrapper = document.createElement('div');
  wrapper.className = 'message-group ai-group';
  wrapper.id = 'typing-wrapper';
  wrapper.innerHTML = `
    <div class="avatar ai-avatar">VO</div>
    <div class="typing-indicator" id="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  DOM.chatHistory().appendChild(wrapper);
  scrollChat();
}

function removeTypingIndicator() {
  const wrapper = $('typing-wrapper');
  if (wrapper) wrapper.remove();
}

function scrollChat() {
  const h = DOM.chatHistory();
  h.scrollTop = h.scrollHeight;
}

function renderMarkdown(text) {
  try {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(text);
  } catch { return escapeHtml(text); }
}

// ═══════════════════════════════════════════════════════════════
// VOICE — STT (Speech Recognition) + TTS (Synthesis)
// ═══════════════════════════════════════════════════════════════

function initVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('Speech Recognition not supported. Using fallback.');
    DOM.micBtn().title = 'Voice input not supported in this browser';
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  recognition.maxAlternatives = 1;
  State.voice.recognition = recognition;

  recognition.onstart = () => {
    State.voice.listening = true;
    DOM.micBtn().classList.add('recording');
    DOM.voiceFb().classList.add('active');
    DOM.voiceLabel().textContent = 'Listening...';
    $('btn-voice').classList.add('active');
    startVoiceVerification();
  };

  recognition.onresult = (event) => {
    let interim = '', final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    DOM.chatInput().value = final || interim;
    DOM.voiceLabel().textContent = interim ? `"${interim}"` : 'Processing...';
    if (final) {
      recognition.stop();
      if (State.voiceLock.active && State.voiceLock.calibrated && !State.voiceLock.verifiedMatch) {
        showToast('Voice signature mismatch. Input ignored.', 'error');
        logReplay('SECURITY', 'Ignored voice prompt: Signature mismatch');
        DOM.chatInput().value = '';
      } else {
        setTimeout(() => sendMessage(final), 300);
      }
    }
  };

  recognition.onend = () => {
    State.voice.listening = false;
    DOM.micBtn().classList.remove('recording');
    DOM.voiceFb().classList.remove('active');
    $('btn-voice').classList.remove('active');
    stopVoiceVerification();
  };

  recognition.onerror = (e) => {
    console.error('Speech recognition error:', e.error);
    DOM.voiceLabel().textContent = `Error: ${e.error}`;
    recognition.stop();
    stopVoiceVerification();
  };
}

function startVoiceInput() {
  if (!State.voice.recognition) { showToast('Voice input not supported in this browser', 'warning'); return; }
  if (State.voice.listening) { State.voice.recognition.stop(); return; }
  try { State.voice.recognition.start(); }
  catch (e) { console.error(e); }
}

function speakText(text) {
  if (!State.voice.ttsEnabled || !State.voice.synth) return;
  // Strip markdown for TTS
  const plain = text.replace(/[#*`_~>\[\]()!]/g, '').replace(/\n+/g, ' ').trim();
  if (!plain) return;

  State.voice.synth.cancel(); // Cancel any ongoing speech
  const utt = new SpeechSynthesisUtterance(plain.substring(0, 500));
  utt.rate = 0.93;  // Calm, authoritative pace
  utt.pitch = 0.85; // Deep, god-like resonance
  utt.volume = 0.9;

  // Prefer a natural voice if available
  const voices = State.voice.synth.getVoices();
  const preferred = voices.find(v => v.name.includes('Google') && v.lang === 'en-US')
    || voices.find(v => v.lang === 'en-US' && !v.localService)
    || voices[0];
  if (preferred) utt.voice = preferred;

  State.voice.synth.speak(utt);
}

// ═══════════════════════════════════════════════════════════════
// CAMERA + MEDIAPIPE GESTURE RECOGNITION
// ═══════════════════════════════════════════════════════════════

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 320, height: 240, facingMode: 'user' },
      audio: false,
    });
    State.camera.stream = stream;
    State.camera.active = true;
    DOM.cameraFeed().srcObject = stream;
    DOM.cameraOverlay().style.display = 'block';
    $('btn-camera').classList.add('active');
    logReplay('CAMERA', 'Camera stream started');
    initGestureDetection();
  } catch (e) {
    showToast(`Camera access denied: ${e.message}`, 'error');
  }
}

function stopCamera() {
  if (State.camera.stream) {
    State.camera.stream.getTracks().forEach(t => t.stop());
    State.camera.stream = null;
  }
  State.camera.active = false;
  DOM.cameraOverlay().style.display = 'none';
  $('btn-camera').classList.remove('active');
  logReplay('CAMERA', 'Camera stream stopped');
}

function initGestureDetection() {
  // MediaPipe Hands — loaded via CDN in HTML
  if (typeof Hands === 'undefined') {
    console.warn('MediaPipe Hands not loaded. Gesture detection unavailable.');
    DOM.gestureFb().textContent = 'MediaPipe unavailable — gesture detection disabled';
    return;
  }

  const hands = new Hands({
    locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
  });
  hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 0,
    minDetectionConfidence: 0.7,
    minTrackingConfidence: 0.6,
  });
  hands.onResults(onGestureResults);
  State.camera.hands = hands;

  // Process frames manually using standard requestAnimationFrame
  processFrameLoop();
}

async function processFrameLoop() {
  if (!State.camera.active) return;
  if (State.camera.hands && DOM.cameraFeed().readyState === 4) {
    try {
      await State.camera.hands.send({ image: DOM.cameraFeed() });
    } catch (e) {
      console.warn("MediaPipe frame send error", e);
    }
  }
  requestAnimationFrame(processFrameLoop);
}

function onGestureResults(results) {
  const canvas  = DOM.gestureCanvas();
  const video   = DOM.cameraFeed();
  const ctx     = canvas.getContext('2d');

  canvas.width  = video.videoWidth || 320;
  canvas.height = video.videoHeight || 240;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) return;

  const landmarks = results.multiHandLandmarks[0];
  drawHandLandmarks(ctx, landmarks, canvas.width, canvas.height);

  const gesture = classifyGesture(landmarks);
  if (gesture && gesture !== State.camera.lastGesture) {
    State.camera.lastGesture = gesture;
    handleGesture(gesture);
    clearTimeout(State.camera.gestureTimeout);
    State.camera.gestureTimeout = setTimeout(() => { State.camera.lastGesture = null; }, 1500);
  }
}

function drawHandLandmarks(ctx, landmarks, W, H) {
  const connections = [
    [0,1],[1,2],[2,3],[3,4],         // thumb
    [0,5],[5,6],[6,7],[7,8],         // index
    [0,9],[9,10],[10,11],[11,12],    // middle
    [0,13],[13,14],[14,15],[15,16],  // ring
    [0,17],[17,18],[18,19],[19,20],  // pinky
    [5,9],[9,13],[13,17]             // palm
  ];
  ctx.strokeStyle = 'rgba(0,212,255,0.7)';
  ctx.lineWidth = 1.5;
  connections.forEach(([a, b]) => {
    ctx.beginPath();
    ctx.moveTo(landmarks[a].x * W, landmarks[a].y * H);
    ctx.lineTo(landmarks[b].x * W, landmarks[b].y * H);
    ctx.stroke();
  });
  landmarks.forEach(lm => {
    ctx.beginPath();
    ctx.arc(lm.x * W, lm.y * H, 3, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,184,0,0.8)';
    ctx.fill();
  });
}

/**
 * Classify hand gesture from 21 MediaPipe landmarks.
 */
function classifyGesture(lm) {
  if (!lm || lm.length < 21) return null;
  const isExtended = (tip, pip) => lm[tip] && lm[pip] && lm[tip].y < lm[pip].y;

  const thumbUp   = lm[4] && lm[3] && lm[2] && lm[4].y < lm[3].y && lm[4].y < lm[2].y;
  const indexExt  = isExtended(8, 6);
  const middleExt = isExtended(12, 10);
  const ringExt   = isExtended(16, 14);
  const pinkyExt  = isExtended(20, 18);

  const detected = [thumbUp, indexExt, middleExt, ringExt, pinkyExt];

  for (const key in State.customGestures) {
    const cg = State.customGestures[key];
    if (cg && cg.fingers) {
      const match = cg.fingers.every((val, idx) => val === detected[idx]);
      if (match) return key;
    }
  }
  return null;
}

function handleGesture(gestureKey) {
  const cg = State.customGestures[gestureKey];
  if (!cg || !cg.action) return;

  const label = cg.label || `Gesture: ${cg.name}`;
  DOM.gestureFb().textContent = label;
  showToast(label, 'info');
  logReplay('GESTURE', cg.name);

  // Execute Action
  const actionParts = cg.action.split(':');
  const actionType = actionParts[0];
  const actionVal = actionParts[1];

  if (actionType === 'switch-panel') {
    switchPanel(actionVal);
  } else if (actionType === 'start-voice') {
    startVoiceInput();
  } else if (actionType === 'stop-camera') {
    stopCamera();
  } else if (actionType === 'custom-prompt') {
    sendMessage(actionVal);
  }
}

function switchPanelRelative(delta) {
  const panels = ['panel-chat', 'panel-research', 'panel-tasks', 'panel-memory', 'panel-monitor'];
  const cur = panels.indexOf(State.currentPanel);
  const next = (cur + delta + panels.length) % panels.length;
  switchPanel(panels[next]);
}

// ═══════════════════════════════════════════════════════════════
// PANEL SWITCHING
// ═══════════════════════════════════════════════════════════════

function switchPanel(panelId) {
  $$('.panel').forEach(p => p.classList.remove('active'));
  $$('.tab-btn').forEach(b => b.classList.remove('active'));

  $$(`.panel`).forEach(p => { if (p.id === panelId) p.classList.add('active'); });
  $$('.tab-btn').forEach(b => { if (b.dataset.panel === panelId) b.classList.add('active'); });

  State.currentPanel = panelId;
  if (panelId === 'panel-monitor') refreshPluginList();
}

// ═══════════════════════════════════════════════════════════════
// RESEARCH ENGINE
// ═══════════════════════════════════════════════════════════════

async function runResearch(query) {
  if (!query) return;
  const results = $('research-results');
  const progress = $('research-progress');
  const fill = $('research-fill');
  const label = $('research-label');

  results.innerHTML = '';
  progress.style.display = 'block';
  fill.style.width = '10%';
  label.textContent = 'Querying SearXNG...';
  logReplay('RESEARCH', `Query: ${query.substring(0, 50)}`);

  try {
    fill.style.width = '40%';
    label.textContent = 'Fetching results from self-hosted SearXNG...';

    const isDeep = $('deep-mode-toggle')?.checked ?? true;
    const resp = await fetch('/api/v1/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, num_results: 8, deep: isDeep }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status} — SearXNG may not be running`);
    const data = await resp.json();

    fill.style.width = '80%';
    label.textContent = 'Rendering results...';

    const items = data.results || [];
    if (!items.length) {
      results.innerHTML = '<div class="research-empty"><div class="empty-icon">◉</div><div class="empty-text">No results — start SearXNG with docker compose up</div></div>';
    } else {
      items.forEach(r => {
        const card = document.createElement('div');
        card.className = 'research-result-card';
        card.innerHTML = `
          <div class="result-title"><a href="${escapeHtml(r.url || '#')}" target="_blank" rel="noopener">${escapeHtml(r.title || 'No title')}</a></div>
          <div class="result-url">${escapeHtml(r.url || '')}</div>
          <div class="result-snippet">${escapeHtml(r.snippet || r.content || '')}</div>`;
        results.appendChild(card);
      });
    }

    if ($('summarize-toggle')?.checked && State.connected && items.length) {
      const summary = items.map(r => `${r.title}: ${r.snippet || ''}`).slice(0, 4).join('\n');
      sendMessage(`Summarize these search results for "${query}":\n${summary}`);
      switchPanel('panel-chat');
    }

    fill.style.width = '100%';
    label.textContent = `Done — ${items.length} results`;
    setTimeout(() => { progress.style.display = 'none'; }, 1500);
    showToast(`Found ${items.length} results`, 'success');

  } catch (e) {
    progress.style.display = 'none';
    results.innerHTML = `<div class="research-result-card"><div class="result-title" style="color:var(--red)">Search Error</div><div class="result-snippet">${escapeHtml(e.message)}<br><em>Tip: Run <code>docker compose up searxng</code> to start the local search engine.</em></div></div>`;
    showToast('Research engine error — is SearXNG running?', 'error');
  }
}

// ═══════════════════════════════════════════════════════════════
// MEMORY OPERATIONS
// ═══════════════════════════════════════════════════════════════

async function queryVectorMemory(query) {
  if (!query) return;
  const container = $('vector-results');
  container.innerHTML = '<div class="mem-empty">Searching ChromaDB...</div>';

  try {
    const resp = await fetch('/api/v1/memory/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: 5 }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const results = data.results || [];

    if (!results.length) {
      container.innerHTML = '<div class="mem-empty">No relevant memories found for this query.</div>';
      return;
    }
    container.innerHTML = '';
    results.forEach(r => {
      const chunk = document.createElement('div');
      chunk.className = 'mem-chunk';
      const score = r.score ? (r.score * 100).toFixed(0) + '%' : '';
      chunk.innerHTML = `
        <div class="mem-chunk-source">${escapeHtml(r.source || 'memory')} ${score ? `· <span style="color:var(--cyan)">${score} match</span>` : ''}</div>
        <div class="mem-chunk-content">${escapeHtml(r.content || '')}</div>`;
      container.appendChild(chunk);
    });
    logReplay('MEMORY', `Vector query returned ${results.length} chunks`);
  } catch (e) {
    container.innerHTML = `<div class="mem-empty">Error: ${escapeHtml(e.message)}</div>`;
  }
}

async function queryKnowledgeGraph(query) {
  if (!query) return;
  const container = $('kg-results');
  container.innerHTML = '<div class="mem-empty">Querying knowledge graph...</div>';

  try {
    const resp = await fetch('/api/v1/memory/kg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const ctx = data.context || '';

    if (!ctx || ctx.includes('No entities')) {
      container.innerHTML = '<div class="mem-empty">No matching entities found in the knowledge graph.</div>';
      return;
    }
    container.innerHTML = '';
    ctx.split('\n').filter(Boolean).forEach(line => {
      const chunk = document.createElement('div');
      chunk.className = 'mem-chunk';
      chunk.innerHTML = `<div class="mem-chunk-content">${escapeHtml(line)}</div>`;
      container.appendChild(chunk);
    });
    logReplay('MEMORY', `KG query returned context for "${query}"`);
  } catch (e) {
    container.innerHTML = `<div class="mem-empty">Error: ${escapeHtml(e.message)}</div>`;
  }
}

async function storeMemory() {
  const content    = $('store-content').value.trim();
  const collection = $('store-collection').value.trim() || 'vibhu_oska_memory';
  const tagsRaw    = $('store-tags').value.trim();
  const fb         = $('store-feedback');

  if (!content) { showToast('Enter content to store', 'warning'); return; }

  fb.textContent = 'Storing in ChromaDB...';
  try {
    const resp = await fetch('/api/v1/memory/store', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        source: 'dashboard',
        collection,
        metadata: parseTagsString(tagsRaw),
      }),
    });
    if (resp.ok) {
      const d = await resp.json();
      fb.textContent = `✓ Stored ${d.chars} chars in ${d.collection}`;
      $('store-content').value = '';
      logReplay('MEMORY', `Stored ${content.length} chars to ${collection}`);
      showToast('Memory stored in ChromaDB', 'success');
    } else {
      fb.textContent = `Error: HTTP ${resp.status}`;
    }
  } catch (e) {
    fb.textContent = `Error: ${e.message}`;
  }
}

function parseTagsString(raw) {
  if (!raw) return {};
  const tags = {};
  raw.split(',').forEach(pair => {
    const [k, v] = pair.split(':').map(s => s.trim());
    if (k && v) tags[k] = v;
  });
  return tags;
}

// ═══════════════════════════════════════════════════════════════
// RLHF FEEDBACK (Training Signal)
// ═══════════════════════════════════════════════════════════════

function showFeedbackBar(requestId) {
  const bar = DOM.feedbackBar();
  bar.style.display = 'flex';
  bar.dataset.rid = requestId || '';
  clearTimeout(bar._timeout);
  bar._timeout = setTimeout(() => hideFeedbackBar(), 15000);
}

function hideFeedbackBar() {
  DOM.feedbackBar().style.display = 'none';
}

async function submitFeedback(approved) {
  const requestId = DOM.feedbackBar().dataset.rid;
  hideFeedbackBar();

  try {
    await fetch('/api/v1/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: 'feedback.signal',
        source: 'dashboard',
        payload: {
          request_id: requestId,
          approved,
          content: State.lastAiContent.substring(0, 500),
        },
      }),
    });
    showToast(approved ? 'Positive signal captured for training data' : 'Negative signal recorded for model refinement', approved ? 'success' : 'warning');
    logReplay('RLHF', `Feedback: ${approved ? 'APPROVED' : 'REJECTED'} for req ${requestId?.substring(0,8)}`);
  } catch (e) {
    showToast('Feedback submission failed', 'error');
  }
}

// ═══════════════════════════════════════════════════════════════
// TASKS & REPLAY LOG
// ═══════════════════════════════════════════════════════════════

function addTaskToList(taskId, prompt) {
  const list = DOM.taskList();
  const empty = list.querySelector('.task-empty');
  if (empty) empty.remove();

  const item = document.createElement('div');
  item.className = 'task-item';
  item.id = `task-${taskId}`;
  item.innerHTML = `
    <div class="task-status-dot pending" id="dot-${taskId}"></div>
    <div class="task-info">
      <div class="task-id">${taskId.substring(0, 16)}...</div>
      <div class="task-prompt">${escapeHtml(prompt.substring(0, 80))}</div>
    </div>
    <div class="task-time">${getTime()}</div>`;
  list.insertBefore(item, list.firstChild);

  // Keep max 20 tasks in list
  while (list.children.length > 20) list.removeChild(list.lastChild);
}

function updateTask(taskId, status) {
  const dot = $(`dot-${taskId}`);
  if (dot) {
    dot.className = `task-status-dot ${status}`;
    if (status !== 'pending') State.taskCounts.active = Math.max(0, State.taskCounts.active - 1);
    updateTaskCounters();
  }
}

function updateTaskCounters() {
  $('t-active').textContent    = State.taskCounts.active;
  $('t-completed').textContent = State.taskCounts.completed;
  $('t-failed').textContent    = State.taskCounts.failed;
  $('t-cache').textContent     = State.taskCounts.cache;
}

function logReplay(action, detail) {
  const log = DOM.replayLog();
  const empty = log.querySelector('.replay-empty');
  if (empty) empty.remove();

  const entry = document.createElement('div');
  entry.className = 'replay-entry';
  entry.innerHTML = `<span class="replay-ts">${getTime()}</span><span class="replay-action">[${action}]</span><span class="replay-detail">${escapeHtml(detail)}</span>`;
  log.insertBefore(entry, log.firstChild);

  while (log.children.length > 50) log.removeChild(log.lastChild);
}

// ═══════════════════════════════════════════════════════════════
// SESSION MANAGEMENT
// ═══════════════════════════════════════════════════════════════

window.newSession = function() {
  // Generate a new UUID for the session
  State.currentSession = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
  // Clear chat history UI
  const history = DOM.chatHistory();
  history.innerHTML = `
    <div class="message-group ai-group">
      <div class="avatar ai-avatar">VO</div>
      <div class="message-bubble ai">
        <div class="msg-content">
          New session initialized. <strong>Vibhu-Oska AI-OS</strong> ready.<br><br>
          <em>Session ID: ${State.currentSession.slice(0, 8)}...</em>
        </div>
        <div class="msg-meta">System · ${new Date().toLocaleTimeString()}</div>
      </div>
    </div>`;
  showToast('New session started', 'success');
  logReplay('SESSION', `New session: ${State.currentSession.slice(0, 8)}`);
  loadSessionHistory();
};

// ═══════════════════════════════════════════════════════════════
// SYSTEM STATUS POLLING
// ═══════════════════════════════════════════════════════════════

async function pollStatus() {
  try {
    const resp = await fetch('/status');
    if (!resp.ok) return;
    const data = await resp.json();

    const upSec = data.system?.uptime_seconds || 0;
    const h = Math.floor(upSec / 3600);
    const m = Math.floor((upSec % 3600) / 60);
    const s = Math.floor(upSec % 60);
    $('m-uptime').textContent  = `${h}h ${m}m ${s}s`;
    $('m-plugins').textContent = data.plugins?.length ?? 0;
    $('m-clients').textContent = data.event_bus?.ws_clients_connected ?? 0;
    $('m-tier').textContent    = data.system?.tier ?? 'Private';
  } catch { /* Silent fail */ }

  try {
    const hresp = await fetch('/health');
    if (hresp.ok) {
      const hdata = await hresp.json();
      const running = hdata.event_bus_running;
      DOM.statusDot().className = `status-dot${running ? ' connected' : ''}`;
      DOM.statusText().textContent = running ? 'ONLINE' : 'DEGRADED';
    }
  } catch { /* Silent fail */ }

  // Refresh KG node / edge counts from the dedicated count endpoint
  try {
    const kgResp = await fetch('/api/v1/memory/kg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: '__count__', top_k: 1 }),
    });
    if (kgResp.ok) {
      const kgData = await kgResp.json();
      const n = kgData.node_count ?? 0;
      const e = kgData.edge_count ?? 0;
      const nc = $('kg-nodes-count'); if (nc) nc.textContent = n + ' Nodes';
      const ec = $('kg-edges-count'); if (ec) ec.textContent = e + ' Edges';
      const mk = $('m-kg'); if (mk) mk.textContent = n + ' / ' + e + 'e';
    }
  } catch { /* Silent fail */ }
}



async function refreshPluginList() {
  try {
    const resp = await fetch('/api/v1/plugins');
    if (!resp.ok) return;
    const data = await resp.json();
    const list = $('plugin-list');
    list.innerHTML = '';

    (data.plugins || []).forEach(p => {
      const statusClass = { 1: 'healthy', 2: 'degraded', 0: 'unknown' }[p.status] || 'unknown';
      const item = document.createElement('div');
      item.className = 'plugin-item';
      item.innerHTML = `
        <div class="plugin-dot ${statusClass}"></div>
        <span class="plugin-name">${escapeHtml(p.name)}</span>
        <span class="plugin-version">v${p.version || '?'}</span>
        <span class="plugin-target">${['AUTO','CPU','GPU','NPU'][p.preferred_target] || 'CPU'}</span>`;
      list.appendChild(item);
    });

    if (!data.plugins?.length) list.innerHTML = '<div class="plugin-empty">No plugins registered</div>';
  } catch { /* Silent fail */ }
}

function appendAlert(title, description) {
  const list = $('alerts-list');
  const empty = list.querySelector('.alert-empty');
  if (empty) empty.remove();
  const item = document.createElement('div');
  item.className = 'alert-item';
  item.innerHTML = `<strong>${escapeHtml(title)}</strong> — ${escapeHtml(description)} <span style="color:var(--text-dim); font-size:10px">${getTime()}</span>`;
  list.insertBefore(item, list.firstChild);
  while (list.children.length > 10) list.removeChild(list.lastChild);
}

// ═══════════════════════════════════════════════════════════════
// CHARTS (Monitor Panel)
// ═══════════════════════════════════════════════════════════════

function initCharts() {
  const chartOpts = (label, color) => ({
    type: 'line',
    data: {
      labels: Array(20).fill(''),
      datasets: [{ label, data: Array(20).fill(0), borderColor: color, borderWidth: 2, fill: true, backgroundColor: color.replace(')', ',0.08)').replace('rgb', 'rgba'), pointRadius: 0, tension: 0.4 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: { display: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: 'rgba(232,238,255,0.4)', font: { size: 9 } } },
      },
      plugins: { legend: { display: false } },
    },
  });

  const ec = $('chart-events');
  const lc = $('chart-latency');
  if (ec) {
    const evOpts = chartOpts('Events', 'rgb(0,212,255)');
    evOpts.data.datasets[0].data = State.charts.eventData;
    State.charts.events = new Chart(ec, evOpts);
  }
  if (lc) {
    const latOpts = chartOpts('Latency (ms)', 'rgb(255,184,0)');
    latOpts.data.datasets[0].data = State.charts.latencyData;
    State.charts.latency = new Chart(lc, latOpts);
  }
}

// ═══════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════

function showToast(message, type = 'info') {
  const container = DOM.toastCont();
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'success' ? 'success' : type === 'error' ? 'error' : type === 'warning' ? 'warning' : ''}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════

function escapeHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function getTime() {
  const d = new Date();
  return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}:${d.getSeconds().toString().padStart(2,'0')}`;
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

// ═══════════════════════════════════════════════════════════════
// PITCH DETECTION & SECURITY LOCKS
// ═══════════════════════════════════════════════════════════════

function detectPitch(buffer, sampleRate) {
  const SIZE = buffer.length;
  let rms = 0;
  for (let i = 0; i < SIZE; i++) {
    const val = buffer[i];
    rms += val * val;
  }
  rms = Math.sqrt(rms / SIZE);
  if (rms < 0.01) return -1;

  let r1 = 0, r2 = SIZE - 1;
  const thres = 0.2;
  for (let i = 0; i < SIZE / 2; i++) {
    if (Math.abs(buffer[i]) < thres) { r1 = i; break; }
  }
  for (let i = SIZE - 1; i >= SIZE / 2; i--) {
    if (Math.abs(buffer[i]) < thres) { r2 = i; break; }
  }

  const buf = buffer.subarray(r1, r2);
  const len = buf.length;
  if (len < 64) return -1;
  const c = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    for (let j = 0; j < len - i; j++) {
      c[i] += buf[j] * buf[j + i];
    }
  }

  let d = 0;
  while (c[d] > c[d + 1]) d++;
  let maxval = -1, maxpos = -1;
  for (let i = d; i < len; i++) {
    if (c[i] > maxval) { maxval = c[i]; maxpos = i; }
  }
  let T0 = maxpos;

  let x1 = c[T0 - 1], x2 = c[T0], x3 = c[T0 + 1];
  let a = (x1 + x3 - 2 * x2) / 2;
  let b = (x3 - x1) / 2;
  if (a) T0 = T0 - b / (2 * a);

  return sampleRate / T0;
}

function initCustomGestures() {
  const defaults = {
    thumbs_up: { name: 'Thumbs Up', fingers: [true, false, false, false, false], action: 'custom-prompt:status', label: 'STATUS Check' },
    open_palm: { name: 'Open Palm', fingers: [true, true, true, true, true], action: 'stop-camera', label: 'STOP Camera' },
    pointing_left: { name: 'Point Left', fingers: [false, true, false, false, false], action: 'switch-panel:panel-chat', label: 'CHAT Panel' },
    call_me: { name: 'Call Me', fingers: [true, false, false, false, true], action: 'start-voice', label: 'VOICE Input' }
  };
  
  let saved = localStorage.getItem('creator_custom_gestures');
  if (!saved) {
    localStorage.setItem('creator_custom_gestures', JSON.stringify(defaults));
    State.customGestures = defaults;
  } else {
    State.customGestures = JSON.parse(saved);
  }
}

function renderGestureList() {
  const container = $('custom-gesture-list');
  if (!container) return;
  container.innerHTML = '';
  
  for (const key in State.customGestures) {
    const cg = State.customGestures[key];
    const item = document.createElement('div');
    item.style = 'display:flex; justify-content:space-between; align-items:center; font-size:11px; padding:4px; border-bottom:1px solid var(--border-subtle); color:var(--text-secondary);';
    item.innerHTML = `
      <span><strong>${cg.name}</strong> (${cg.fingers.map((f, i) => f ? ['T','I','M','R','P'][i] : '').filter(Boolean).join(',') || 'None'})</span>
      <span style="color:var(--cyan); cursor:pointer;" onclick="deleteGesture('${key}')">Delete</span>
    `;
    container.appendChild(item);
  }
}

window.deleteGesture = function(key) {
  delete State.customGestures[key];
  localStorage.setItem('creator_custom_gestures', JSON.stringify(State.customGestures));
  renderGestureList();
  showToast('Gesture deleted', 'info');
};

async function calibrateVoice() {
  if (State.voiceLock.calibrating) return;
  State.voiceLock.calibrating = true;
  $('voice-lock-status').textContent = 'Profile Status: Calibrating (Speak now)...';
  showToast('Calibration active. Speak normally into your mic.', 'info');

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);
    const pitches = [];
    const startTime = Date.now();

    const checkPitchLoop = () => {
      if (Date.now() - startTime > 3000) {
        stream.getTracks().forEach(t => t.stop());
        audioContext.close();
        
        const valid = pitches.filter(p => p > 50 && p < 400);
        if (valid.length === 0) {
          $('voice-lock-status').textContent = 'Profile Status: Calibration Failed (No speech)';
          showToast('Voice calibration failed. Try again.', 'error');
          State.voiceLock.calibrating = false;
          return;
        }

        const avg = valid.reduce((sum, val) => sum + val, 0) / valid.length;
        State.voiceLock.creatorPitch = avg;
        State.voiceLock.calibrated = true;
        localStorage.setItem('creator_voice_pitch', avg.toString());
        $('voice-lock-status').textContent = `Profile Status: Calibrated (${avg.toFixed(0)}Hz)`;
        showToast('Voice Profile Calibrated successfully!', 'success');
        State.voiceLock.calibrating = false;
      } else {
        analyser.getFloatTimeDomainData(dataArray);
        const pitch = detectPitch(dataArray, audioContext.sampleRate);
        if (pitch > 0) pitches.push(pitch);
        requestAnimationFrame(checkPitchLoop);
      }
    };

    checkPitchLoop();

  } catch (e) {
    $('voice-lock-status').textContent = 'Profile Status: Access Denied';
    showToast('Mic access denied for calibration', 'error');
    State.voiceLock.calibrating = false;
  }
}

let micStreamForVerification = null;
let micContextForVerification = null;

async function startVoiceVerification() {
  if (!State.voiceLock.active || !State.voiceLock.calibrated) {
    State.voiceLock.verifiedMatch = true; // bypass if lock is inactive
    return;
  }
  
  try {
    micStreamForVerification = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    micContextForVerification = new (window.AudioContext || window.webkitAudioContext)();
    const source = micContextForVerification.createMediaStreamSource(micStreamForVerification);
    const analyser = micContextForVerification.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Float32Array(bufferLength);
    
    State.voiceLock.verifiedMatch = false;

    const verifyLoop = () => {
      if (!State.voice.listening) {
        stopVoiceVerification();
        return;
      }
      
      analyser.getFloatTimeDomainData(dataArray);
      const pitch = detectPitch(dataArray, micContextForVerification.sampleRate);
      
      if (pitch > 50 && pitch < 400) {
        const diff = Math.abs(pitch - State.voiceLock.creatorPitch);
        const pctDiff = diff / State.voiceLock.creatorPitch;
        
        if (pctDiff < 0.22) { // 22% variance to accommodate normal pitch shifts
          State.voiceLock.verifiedMatch = true;
          DOM.voiceLabel().textContent = `Matched Creator (${pitch.toFixed(0)}Hz)`;
        } else {
          DOM.voiceLabel().textContent = `Unverified Speaker (${pitch.toFixed(0)}Hz)`;
        }
      }
      
      requestAnimationFrame(verifyLoop);
    };
    
    verifyLoop();
  } catch (e) {
    console.error("Verification audio capture failed", e);
    State.voiceLock.verifiedMatch = true; // bypass on error to avoid soft-lock
  }
}

function stopVoiceVerification() {
  if (micStreamForVerification) {
    micStreamForVerification.getTracks().forEach(t => t.stop());
    micStreamForVerification = null;
  }
  if (micContextForVerification) {
    micContextForVerification.close();
    micContextForVerification = null;
  }
}

// ═══════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════

// ---
// INIT
// ---

document.addEventListener('DOMContentLoaded', () => {
  // Neural background
  initNeuralCanvas();

  // Charts
  initCharts();

  // Voice
  initVoice();
  if (window.speechSynthesis) window.speechSynthesis.getVoices();

  // Custom Gestures Init
  initCustomGestures();
  renderGestureList();

  // Voice Lock Settings Init
  const savedPitch = localStorage.getItem('creator_voice_pitch');
  if (savedPitch) {
    State.voiceLock.creatorPitch = parseFloat(savedPitch);
    State.voiceLock.calibrated = true;
    $('voice-lock-status').textContent = 'Profile Status: Calibrated (' + State.voiceLock.creatorPitch.toFixed(0) + 'Hz)';
  }
  
  const savedActive = localStorage.getItem('creator_voice_lock_active');
  if (savedActive === 'true') {
    State.voiceLock.active = true;
    $('voice-lock-toggle').checked = true;
    $('btn-voice-lock').classList.add('active');
  }

  // WebSocket
  connectWebSocket();

  // Initial status poll
  pollStatus();
  setInterval(pollStatus, 5000);

  // Session history — load immediately then every 30s
  loadSessionHistory();
  setInterval(loadSessionHistory, 30000);


  // Tab navigation
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
  });

  // Send button and input
  DOM.sendBtn().addEventListener('click', () => sendMessage());
  DOM.chatInput().addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  DOM.chatInput().addEventListener('input', () => autoResizeTextarea(DOM.chatInput()));

  // Mic button
  DOM.micBtn().addEventListener('click', startVoiceInput);
  $('btn-voice').addEventListener('click', startVoiceInput);

  // Camera button
  $('btn-camera').addEventListener('click', () => {
    if (State.camera.active) stopCamera();
    else startCamera();
  });
  $('camera-close').addEventListener('click', stopCamera);

  // Voice Lock events
  $('btn-voice-lock').addEventListener('click', () => {
    if (!State.voiceLock.calibrated) {
      showToast('Calibrate voice profile first!', 'warning');
      switchPanel('panel-monitor');
      return;
    }
    State.voiceLock.active = !State.voiceLock.active;
    $('voice-lock-toggle').checked = State.voiceLock.active;
    $('btn-voice-lock').classList.toggle('active', State.voiceLock.active);
    localStorage.setItem('creator_voice_lock_active', State.voiceLock.active.toString());
    showToast(State.voiceLock.active ? 'Voice Lock Active' : 'Voice Lock Disabled', 'info');
  });

  $('voice-lock-toggle').addEventListener('change', (e) => {
    if (!State.voiceLock.calibrated) {
      showToast('Calibrate voice profile first!', 'warning');
      e.target.checked = false;
      return;
    }
    State.voiceLock.active = e.target.checked;
    $('btn-voice-lock').classList.toggle('active', State.voiceLock.active);
    localStorage.setItem('creator_voice_lock_active', State.voiceLock.active.toString());
    showToast(State.voiceLock.active ? 'Voice Lock Active' : 'Voice Lock Disabled', 'info');
  });

  $('btn-voice-calibrate').addEventListener('click', calibrateVoice);

  // Add Gesture event
  $('btn-add-gesture').addEventListener('click', () => {
    const name = $('gest-name').value.trim();
    if (!name) { showToast('Enter gesture name', 'warning'); return; }
    
    const key = name.toLowerCase().replace(/\s+/g, '_');
    const fingers = [
      $('f-thumb').checked,
      $('f-index').checked,
      $('f-middle').checked,
      $('f-ring').checked,
      $('f-pinky').checked
    ];
    const action = $('gest-action').value;
    
    State.customGestures[key] = {
      name,
      fingers,
      action,
      label: 'Triggered: ' + name
    };
    
    localStorage.setItem('creator_custom_gestures', JSON.stringify(State.customGestures));
    renderGestureList();
    
    $('gest-name').value = '';
    $('f-thumb').checked = false;
    $('f-index').checked = false;
    $('f-middle').checked = false;
    $('f-ring').checked = false;
    $('f-pinky').checked = false;
    
    showToast('Gesture saved successfully', 'success');
  });

  // Mode buttons
  $('btn-search-mode').addEventListener('click', () => {
    const isActive = $('btn-search-mode').classList.toggle('active');
    State.currentMode = isActive ? 'RESEARCH' : 'CHAT';
    $('mode-indicator').textContent = State.currentMode;
    if (isActive) { $('btn-code-mode').classList.remove('active'); $('btn-memory-query').classList.remove('active'); }
  });
  $('btn-code-mode').addEventListener('click', () => {
    const isActive = $('btn-code-mode').classList.toggle('active');
    State.currentMode = isActive ? 'CODE' : 'CHAT';
    $('mode-indicator').textContent = State.currentMode;
    if (isActive) { $('btn-search-mode').classList.remove('active'); $('btn-memory-query').classList.remove('active'); }
  });
  $('btn-memory-query').addEventListener('click', () => {
    const isActive = $('btn-memory-query').classList.toggle('active');
    State.currentMode = isActive ? 'MEMORY' : 'CHAT';
    $('mode-indicator').textContent = State.currentMode;
    if (isActive) { $('btn-search-mode').classList.remove('active'); $('btn-code-mode').classList.remove('active'); }
  });

  // Research panel
  $('research-btn').addEventListener('click', () => runResearch($('research-input').value.trim()));
  $('research-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') runResearch(e.target.value.trim()); });

  // Memory panel
  $$('.mem-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.mem-tab').forEach(t => t.classList.remove('active'));
      $$('.mem-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      $(tab.dataset.mtab)?.classList.add('active');
    });
  });
  $('vector-search-btn').addEventListener('click', () => queryVectorMemory($('vector-query').value.trim()));
  $('vector-query').addEventListener('keydown', (e) => { if (e.key === 'Enter') queryVectorMemory(e.target.value.trim()); });
  $('kg-search-btn').addEventListener('click', () => queryKnowledgeGraph($('kg-query').value.trim()));
  $('kg-query').addEventListener('keydown', (e) => { if (e.key === 'Enter') queryKnowledgeGraph(e.target.value.trim()); });
  $('store-btn').addEventListener('click', storeMemory);

  // KG ingest button
  const kgIngestBtn = $('kg-ingest-btn');
  if (kgIngestBtn) {
    kgIngestBtn.addEventListener('click', async () => {
      const text = $('kg-ingest-text').value.trim();
      const fb   = $('kg-ingest-feedback');
      if (!text) { showToast('Enter text to ingest', 'warning'); return; }
      fb.textContent = 'Extracting entities...';
      try {
        const resp = await fetch('/api/v1/memory/kg/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, source: 'manual_ingest' }),
        });
        const data = await resp.json();
        if (resp.ok) {
          fb.textContent = `✓ ${data.entities_extracted} entities ingested into KG`;
          $('kg-ingest-text').value = '';
          showToast(`KG updated — ${data.entities_extracted} entities extracted`, 'success');
          logReplay('GRAG', `Ingested ${data.entities_extracted} entities`);
        } else {
          fb.textContent = `Error: ${data.detail || resp.status}`;
        }
      } catch (e) {
        fb.textContent = `Error: ${e.message}`;
      }
    });
  }

  // Feedback bar
  $('fb-approve').addEventListener('click', () => submitFeedback(true));
  $('fb-reject').addEventListener('click', () => submitFeedback(false));
  $('fb-close').addEventListener('click', hideFeedbackBar);


  // Real hardware metrics polling
  setInterval(async () => {
    try {
      const resp = await fetch('/api/v1/telemetry');
      if (!resp.ok) return;
      const data = await resp.json();
      if (data.available && data.thermal) {
        const t = data.thermal;
        const vram = t.gpu_util_pct || 0;
        const cpu  = t.cpu_util_pct || 0;
        const ram  = t.ram_util_pct || 0;
        const temp = t.gpu_temp_c || 0;
        $('bar-vram').style.width = vram + '%'; $('val-vram').textContent = vram.toFixed(0) + '%';
        $('bar-cpu').style.width  = cpu  + '%'; $('val-cpu').textContent  = cpu.toFixed(0)  + '%';
        $('bar-ram').style.width  = ram  + '%'; $('val-ram').textContent  = ram.toFixed(0)  + '%';
        $('bar-temp').style.width = temp + '%'; $('val-temp').textContent = temp.toFixed(0) + 'C';
      }
    } catch (e) {
      console.warn("Telemetry update failed", e);
    }
  }, 2000);

  showToast('Vibhu-Oska AI-OS dashboard loaded', 'success');
});

// ═══════════════════════════════════════════════════════════════
// TRAINING PANEL
// ═══════════════════════════════════════════════════════════════

function appendTrainLog(msg) {
  const log = $('train-log');
  if (!log) return;
  const empty = log.querySelector('.dim');
  if (empty && empty.textContent.includes('appear here')) empty.remove();

  const entry = document.createElement('div');
  entry.className = 'train-log-entry';
  // Classify by content
  if (msg.includes('[ERROR]') || msg.toLowerCase().includes('error')) entry.classList.add('error');
  else if (msg.includes('[SUCCESS]') || msg.includes('completed')) entry.classList.add('success');
  else if (msg.match(/epoch\s+\d+/i) || msg.includes('loss')) entry.classList.add('epoch');
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  // column-reverse means prepend = appears at bottom visually
  log.insertBefore(entry, log.firstChild);

  // Update status badge
  const statusEl = $('train-log-status');
  if (statusEl) {
    if (msg.includes('[SUCCESS]')) statusEl.textContent = 'Completed ✓';
    else if (msg.includes('[ERROR]')) statusEl.textContent = 'Failed ✗';
    else statusEl.textContent = 'Running...';
  }
}

window.startSovereignTraining = async function() {
  const btn = $('btn-train-sgpt');
  const banner = $('train-status-banner');

  const params = {
    epochs:           parseInt($('sgpt-epochs').value)     || 60,
    batch_size:       parseInt($('sgpt-batch').value)      || 4,
    learning_rate:    $('sgpt-lr').value.trim()            || '5e-4',
    hidden_dimension: parseInt($('sgpt-hidden').value)     || 128,
    layers:           parseInt($('sgpt-layers').value)     || 4,
    attention_heads:  parseInt($('sgpt-heads').value)      || 4,
    vocab_size:       parseInt($('sgpt-vocab').value)      || 2000,
    device:           $('sgpt-device').value               || 'auto',
  };

  btn.disabled = true;
  banner.className = 'train-banner running';
  banner.textContent = `Training started — ${params.epochs} epochs · batch ${params.batch_size} · lr ${params.learning_rate} · device ${params.device}`;
  banner.style.display = 'block';

  appendTrainLog('Initiating Sovereign GPT training pipeline...');
  $('train-log-status').textContent = 'Starting...';
  logReplay('TRAIN', `Sovereign GPT training started — ${params.epochs}ep`);

  try {
    const resp = await fetch('/api/v1/model/train', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    appendTrainLog(`Server: ${data.message || data.status}`);
    showToast('Sovereign GPT training job started. Logs streaming via WebSocket.', 'success');
    banner.className = 'train-banner running';
    banner.textContent = 'Training running in background — watch logs below';
  } catch (e) {
    banner.className = 'train-banner error';
    banner.textContent = `Training failed: ${e.message}`;
    appendTrainLog(`[ERROR] ${e.message}`);
    showToast('Training start failed', 'error');
    btn.disabled = false;
  }
};

window.retrainRouter = async function() {
  const banner = $('train-status-banner');
  banner.className = 'train-banner';
  banner.textContent = 'Router retraining must be run via CLI: python -m Models.router.train';
  banner.style.display = 'block';
  appendTrainLog('[INFO] Router retraining: run "python -m Models.router.train" from project root.');
  showToast('Router retraining must be triggered from CLI', 'warning');
};

window.appendCorpus = async function() {
  const content = $('corpus-append').value.trim();
  if (!content) { showToast('Enter content to append', 'warning'); return; }

  // Auto-detect Q|A format
  const format = content.includes('|') ? 'qa' : 'raw';

  try {
    const resp = await fetch('/api/v1/corpus/append', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: content, format }),
    });
    if (resp.ok) {
      const data = await resp.json();
      $('corpus-append').value = '';
      showToast(`Corpus updated — ${data.words_added} words added`, 'success');
      appendTrainLog(`[CORPUS] Appended ${data.words_added} words (${format.toUpperCase()} format) to training corpus`);
    } else {
      const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
      showToast(`Corpus append failed: ${err.detail || resp.status}`, 'error');
    }
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
  }
};

// ═══════════════════════════════════════════════════════════════
// SESSION HISTORY SIDEBAR
// ═══════════════════════════════════════════════════════════════

async function loadSessionHistory() {
  const container = $('session-history-list');
  if (!container) return;

  try {
    const resp = await fetch('/api/v1/sessions?limit=10');
    if (!resp.ok) return;
    const data = await resp.json();
    const sessions = data.sessions || [];

    if (!sessions.length) {
      container.innerHTML = '<div class="session-item dim">No sessions yet</div>';
      return;
    }

    container.innerHTML = '';
    sessions.forEach(s => {
      const item = document.createElement('div');
      item.className = 'session-item';
      const sid = (s.session_id || s[0] || '').slice(0, 8);
      const uid = s.user_id || s[1] || 'operator';
      const ts  = s.updated_at || s.created_at || s[4] || s[3] || '';
      const time = ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
      item.innerHTML = `
        <div class="session-id">${sid}...</div>
        <div class="session-meta">${uid} · ${time}</div>
      `;
      item.addEventListener('click', () => {
        switchPanel('panel-memory');
        // auto-populate the history query input
        const fullId = s.session_id || s[0] || '';
        showToast(`Session ${sid} selected`, 'info');
      });
      container.appendChild(item);
    });
  } catch (e) {
    if (container) container.innerHTML = '<div class="session-item dim">—</div>';
  }
}

