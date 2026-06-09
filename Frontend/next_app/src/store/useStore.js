import { create } from 'zustand';

export const useStore = create((set, get) => ({
  // Navigation
  activePage: 'dashboard', // dashboard | config | playground | research | code | sandbox | admin | docs
  setActivePage: (page) => set({ activePage: page }),

  // Telemetry (Real-time hardware data fetched from backend)
  telemetry: {
    gpuUtil: 0,
    cpuUtil: 0,
    ramUtil: 0,
    gpuTemp: 0,
    gpuPower: 0,
    uptime: '0h 0m 0s'
  },
  setTelemetry: (telemetry) => set({ telemetry }),

  // Local Model Training Metrics
  training: {
    active: false,
    epoch: 0,
    maxEpochs: 10,
    step: 0,
    loss: 4.5,
    throughput: 0,
    logs: [],
    lossHistory: []
  },
  startTraining: () => set((state) => ({
    training: { ...state.training, active: true, epoch: 0, step: 0, loss: 4.5, logs: ['Training initialized locally.'], lossHistory: [] }
  })),
  stopTraining: () => set((state) => ({
    training: { ...state.training, active: false }
  })),
  updateTrainingMetrics: (metrics) => set((state) => ({
    training: { ...state.training, ...metrics }
  })),

  // Local Chat / Playground (ChatGPT/Gemini style)
  chatHistory: [
    { role: 'assistant', content: 'Vibhu-Oska AI-OS ready. All operations are strictly local. No API connections enabled.', thinking: 'System initialized locally on CPU/GPU framework.' }
  ],
  addChatMessage: (msg) => set((state) => ({
    chatHistory: [...state.chatHistory, msg]
  })),
  clearChatHistory: () => set({
    chatHistory: [
      { role: 'assistant', content: 'Vibhu-Oska AI-OS ready. All operations are strictly local. No API connections enabled.', thinking: 'System initialized locally on CPU/GPU framework.' }
    ]
  }),

  // Local Knowledge Graph & Citations (Perplexity style)
  searchQuery: '',
  searchResults: null,
  setSearch: (query, results) => set({ searchQuery: query, searchResults: results }),

  // Local Code Workspace (Claude Code style)
  codeFiles: [
    { name: 'app.py', status: 'healthy', size: '22KB' },
    { name: 'cognition.py', status: 'healthy', size: '5.8KB' },
    { name: 'backup1.py', status: 'healed', size: '3.1KB' }
  ],
  codeLogs: ['Ready for autonomous AST diagnostics.'],
  addCodeLog: (log) => set((state) => ({ codeLogs: [log, ...state.codeLogs] })),

  // Odyssey Sandbox (Agent world grid coordinates)
  agents: [
    { id: 'Agent-Alpha', x: 2, y: 3, state: 'Searching Memory', log: 'Querying vector paths' },
    { id: 'Agent-Beta', x: 7, y: 5, state: 'Analyzing Code', log: 'Parsing AST for apps' },
    { id: 'Agent-Gamma', x: 4, y: 8, state: 'Training Router', log: 'Optimizing weight gradients' }
  ],
  updateAgentPositions: () => set((state) => ({
    agents: state.agents.map(a => {
      const dx = Math.floor(Math.random() * 3) - 1;
      const dy = Math.floor(Math.random() * 3) - 1;
      const newX = Math.max(0, Math.min(10, a.x + dx));
      const newY = Math.max(0, Math.min(10, a.y + dy));
      return { ...a, x: newX, y: newY };
    })
  })),

  // Self-Updater
  updaterStatus: 'idle', // idle | testing | patching | verification
  updaterLogs: ['Self-healing system ready.'],
  setUpdater: (status, logs) => set({ updaterStatus: status, updaterLogs: logs }),
  addUpdaterLog: (log) => set((state) => ({ updaterLogs: [log, ...state.updaterLogs] }))
}));
