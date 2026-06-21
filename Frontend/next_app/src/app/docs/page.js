'use client';

import React from 'react';
import { 
  BookOpen, 
  Cpu, 
  Layers, 
  Activity, 
  Mic, 
  ShieldAlert, 
  GitBranch,
  Network
} from 'lucide-react';

export default function DocsPage() {
  return (
    <div className="space-y-6 max-w-4xl">
      
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
          SYSTEM DOCUMENTATION
        </h1>
        <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
          Technical specifications, architectural blueprints, and module routing layouts for Vibhu-Oska.
        </p>
      </div>

      {/* Grid of Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 font-mono text-xs text-[#E8EEFF]/70">
        
        {/* Core Architecture */}
        <div className="glass-panel rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-white/5 pb-2 text-[#00D4FF] font-bold">
            <Layers className="w-4 h-4" />
            <span>Sovereign Local Architecture</span>
          </div>
          <p className="leading-relaxed text-[#E8EEFF]/65">
            Vibhu-Oska runs strictly locally. It decouples the UI layer from the core via a localized ZeroMQ-backed event loop that triggers background tasks without hosted network dependencies.
          </p>
          <div className="bg-black/25 rounded-lg p-3 text-[10px] space-y-1">
            <div className="flex justify-between text-[#00D4FF]">
              <span>Ingress Gateway</span>
              <span>FastAPI (Port 8000)</span>
            </div>
            <div className="flex justify-between">
              <span>Event Loop Bus</span>
              <span>ZeroMQ (Ports 5555-5558)</span>
            </div>
            <div className="flex justify-between">
              <span>Inference Core</span>
              <span>PyTorch/CPU/GPU Fallback</span>
            </div>
          </div>
        </div>

        {/* Competitor Pruning */}
        <div className="glass-panel rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-white/5 pb-2 text-[#7B2FBE] font-bold">
            <GitBranch className="w-4 h-4" />
            <span>Competitor Capability Union</span>
          </div>
          <p className="leading-relaxed text-[#E8EEFF]/65">
            By analyzing OpenAI (ChatGPT), Google (Gemini), Perplexity, and Anthropic (Claude Code), we configured a pruned local layout that keeps only the core features.
          </p>
          <ul className="list-disc list-inside space-y-1 text-[10px] text-[#E8EEFF]/55">
            <li><strong className="text-white">ChatGPT / Gemini:</strong> Expandable R1-style raw reasoning + TTS synthesis parameters.</li>
            <li><strong className="text-white">Perplexity Search:</strong> Local SearXNG indexing + markdown citations.</li>
            <li><strong className="text-white">Claude Code:</strong> Static AST codebase analyzer + Ruff diagnostics linting.</li>
          </ul>
        </div>

        {/* Voice Signature Lock */}
        <div className="glass-panel rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-white/5 pb-2 text-[#FFB800] font-bold">
            <Mic className="w-4 h-4" />
            <span>Audio Voice Lock Filter</span>
          </div>
          <p className="leading-relaxed text-[#E8EEFF]/65">
            The Voice Signature Calibration uses a time-domain autocorrelation pitch frequency scanner. When toggled, the microphone transcription input ignores any signals outside the creator's calibrated pitch profile.
          </p>
          <div className="bg-black/25 rounded-lg p-3 text-[10px]">
            <span className="text-white">Autocorrelation math:</span><br/>
            <code className="text-[#FFB800]">r(k) = Σ [x(t) * x(t + k)]</code> for period identification. Locked to a 20% variance threshold.
          </div>
        </div>

        {/* Closed-loop Self-Correction */}
        <div className="glass-panel rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 border-b border-white/5 pb-2 text-[#FF4444] font-bold">
            <ShieldAlert className="w-4 h-4" />
            <span>Self-Healing Engine</span>
          </div>
          <p className="leading-relaxed text-[#E8EEFF]/65">
            Self-updater manages codebase status. It executes tests using the `TestingFramework`, extracts traceback errors, sends them to AST, and applies healing patches in a closed correction loop.
          </p>
          <div className="bg-black/25 rounded-lg p-3 text-[10px] space-y-1">
            <div className="flex justify-between">
              <span>Tests Suite</span>
              <span className="text-[#22D3A0]">pytest</span>
            </div>
            <div className="flex justify-between">
              <span>Linter Engine</span>
              <span className="text-[#22D3A0]">Ruff (fast static check)</span>
            </div>
            <div className="flex justify-between">
              <span>Correction Code</span>
              <span className="text-[#22D3A0]">Local replacement patches</span>
            </div>
          </div>
        </div>

      </div>

      {/* Mermaid Diagram Representation (in HTML/CSS) */}
      <div className="glass-panel rounded-xl p-5 font-mono space-y-4">
        <div className="flex items-center gap-2 border-b border-white/5 pb-3 text-white font-bold">
          <Network className="w-4 h-4 text-[#00D4FF]" />
          <span>Vibhu-Oska Architectural Routing Map</span>
        </div>

        <div className="flex flex-col items-center gap-2 text-[10px] text-center pt-2">
          
          <div className="px-4 py-2 border border-[#00D4FF]/30 bg-[#00D4FF]/5 text-[#00D4FF] rounded-lg w-56 font-bold">
            React Next.js Frontend UI
          </div>
          
          <div className="w-px h-6 bg-[#00D4FF]/35" />

          <div className="px-4 py-2 border border-[#7B2FBE]/30 bg-[#7B2FBE]/5 text-[#D2A0FF] rounded-lg w-56 font-bold">
            API Gateway (FastAPI / Websockets)
          </div>

          <div className="w-px h-6 bg-[#7B2FBE]/35" />

          <div className="px-4 py-2 border border-white/20 bg-black/45 text-white/90 rounded-lg w-72 flex flex-col gap-2 p-3">
            <div className="font-bold border-b border-white/5 pb-1 uppercase text-[8px] tracking-wider text-[#E8EEFF]/40">
              ZeroMQ Event Broker (Event Bus)
            </div>
            <div className="grid grid-cols-2 gap-2 text-[8px] text-[#E8EEFF]/70">
              <div className="border border-white/5 p-1 rounded">Topic Sub: `task.`</div>
              <div className="border border-white/5 p-1 rounded">Topic Pub: `system.`</div>
            </div>
          </div>

          <div className="w-px h-6 bg-white/20" />

          <div className="px-4 py-2 border border-[#FFB800]/30 bg-[#FFB800]/5 text-[#FFB800] rounded-lg w-56 font-bold">
            Plugin Manager & Cognition Core
          </div>

        </div>
      </div>

    </div>
  );
}
