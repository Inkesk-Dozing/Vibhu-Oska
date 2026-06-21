'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  Plus, 
  RefreshCw, 
  Grid, 
  Layers, 
  Navigation,
  Activity,
  Bot
} from 'lucide-react';
import { useStore } from '../../store/useStore';

export default function OdysseySandboxPage() {
  const agents = useStore(state => state.agents);
  const updateAgentPositions = useStore(state => state.updateAgentPositions);
  
  const [running, setRunning] = useState(false);
  const [localAgents, setLocalAgents] = useState(agents);
  const canvasRef = useRef(null);

  // Auto-running loop
  useEffect(() => {
    if (!running) return;

    const interval = setInterval(() => {
      updateAgentPositions();
    }, 1500);

    return () => clearInterval(interval);
  }, [running, updateAgentPositions]);

  // Redraw grid simulation canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    const size = canvas.width = 400;
    const pad = 40;
    const cells = 10;
    const step = (size - pad * 2) / cells;

    const draw = () => {
      // Clear
      ctx.fillStyle = '#060912';
      ctx.fillRect(0, 0, size, size);

      // Draw Grid Lines
      ctx.strokeStyle = 'rgba(0, 212, 255, 0.06)';
      ctx.lineWidth = 1;
      for (let i = 0; i <= cells; i++) {
        const coord = pad + i * step;
        // Vert
        ctx.beginPath();
        ctx.moveTo(coord, pad);
        ctx.lineTo(coord, size - pad);
        ctx.stroke();

        // Horiz
        ctx.beginPath();
        ctx.moveTo(pad, coord);
        ctx.lineTo(size - pad, coord);
        ctx.stroke();
      }

      // Draw Agents
      agents.forEach((agent) => {
        const xCoord = pad + agent.x * step;
        const yCoord = pad + agent.y * step;

        // Draw Glow
        const gradient = ctx.createRadialGradient(xCoord, yCoord, 2, xCoord, yCoord, 12);
        gradient.addColorStop(0, 'rgba(0, 212, 255, 0.6)');
        gradient.addColorStop(1, 'rgba(0, 212, 255, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(xCoord, yCoord, 12, 0, Math.PI * 2);
        ctx.fill();

        // Draw Center
        ctx.fillStyle = '#00D4FF';
        ctx.beginPath();
        ctx.arc(xCoord, yCoord, 4, 0, Math.PI * 2);
        ctx.fill();

        // Draw name label
        ctx.fillStyle = 'rgba(232, 238, 255, 0.5)';
        ctx.font = '8px monospace';
        ctx.fillText(agent.id, xCoord + 6, yCoord - 4);
      });

      // Draw proximity lines between agents if they are close
      ctx.strokeStyle = 'rgba(123, 47, 190, 0.25)';
      ctx.lineWidth = 0.8;
      for (let i = 0; i < agents.length; i++) {
        for (let j = i + 1; j < agents.length; j++) {
          const a = agents[i];
          const b = agents[j];
          const dist = Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2));
          if (dist < 4) {
            ctx.beginPath();
            ctx.moveTo(pad + a.x * step, pad + a.y * step);
            ctx.lineTo(pad + b.x * step, pad + b.y * step);
            ctx.stroke();
          }
        }
      }
    };

    draw();
  }, [agents]);

  const handleStep = () => {
    updateAgentPositions();
  };

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
          ODYSSEY AGENT SANDBOX
        </h1>
        <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
          Simulate local autonomous multi-agent coordinate interactions. Monitors memory paths and AST updates.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        
        {/* Left simulation canvas */}
        <div className="lg:col-span-2 flex flex-col items-center justify-center glass-panel rounded-xl p-5 gap-4">
          <div className="flex justify-between w-full items-center font-mono text-[10px] text-[#E8EEFF]/55 uppercase tracking-wider pb-2 border-b border-white/5">
            <span className="flex items-center gap-1">
              <Grid className="w-3.5 h-3.5 text-[#00D4FF]" /> Coordinates grid
            </span>
            <span>Simulation Frame</span>
          </div>

          <div className="relative border border-[#00D4FF]/10 rounded-xl overflow-hidden shadow-lg shadow-[#00D4FF]/5">
            <canvas ref={canvasRef} className="block w-full max-w-[320px] aspect-square" />
          </div>

          {/* Controls */}
          <div className="flex gap-2 w-full">
            <button 
              onClick={() => setRunning(!running)}
              className={`flex-1 py-2 rounded-lg font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 ${
                running 
                  ? 'bg-[#FF4444]/15 border border-[#FF4444]/40 text-[#FF4444]' 
                  : 'bg-[#00D4FF]/10 border border-[#00D4FF]/30 text-[#00D4FF] hover:bg-[#00D4FF]/20'
              }`}
            >
              {running ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {running ? 'PAUSE CYCLE' : 'RUN CYCLE'}
            </button>

            <button 
              onClick={handleStep}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg font-mono text-xs text-white/80 transition-all active:scale-95"
              title="Manual Grid Step"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right agent listings */}
        <div className="lg:col-span-3 space-y-4">
          
          <div className="flex justify-between items-center font-mono text-[10px] text-[#E8EEFF]/40 uppercase tracking-widest px-1">
            <span>ACTIVE COORDINATE NODES</span>
            <span>COUNT: {agents.length}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <div key={agent.id} className="glass-panel rounded-xl p-4 flex flex-col justify-between space-y-3 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-12 h-12 bg-[#00D4FF]/5 rounded-bl-full pointer-events-none" />
                
                <div className="flex items-center gap-2 border-b border-white/5 pb-2">
                  <Bot className="w-4 h-4 text-[#00D4FF]" />
                  <span className="font-mono text-xs font-bold text-white">{agent.id}</span>
                </div>

                <div className="space-y-1 font-mono text-[10px]">
                  <div className="flex justify-between">
                    <span className="text-[#E8EEFF]/40">COORDINATE</span>
                    <span className="text-[#00D4FF] font-bold">({agent.x}, {agent.y})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E8EEFF]/40">ACTION STATE</span>
                    <span className="text-white/80 truncate">{agent.state}</span>
                  </div>
                </div>

                <div className="bg-black/25 border border-white/5 rounded-lg p-2 font-mono text-[9px] text-[#E8EEFF]/50 mt-1 leading-relaxed min-h-[44px]">
                  <span className="text-[#00D4FF]/60">&gt;&gt;</span> {agent.log}
                </div>
              </div>
            ))}
          </div>

          {/* Sandbox telemetry log console */}
          <div className="glass-panel rounded-xl p-5 space-y-3 font-mono">
            <div className="flex items-center gap-2 text-[10px] text-[#7B2FBE] font-bold uppercase tracking-wider">
              <Layers className="w-3.5 h-3.5" />
              <span>Multi-Agent Event Stream</span>
            </div>

            <div className="bg-black/35 border border-white/5 rounded-lg p-3 text-[10px] text-[#E8EEFF]/60 space-y-1.5 h-[100px] overflow-y-auto">
              <div><span className="text-[#7B2FBE]">&gt;</span> Agent-Alpha reached coordinate ({agents[0].x}, {agents[0].y}).</div>
              <div><span className="text-[#7B2FBE]">&gt;</span> Agent-Beta broadcast state: "{agents[1].state}".</div>
              <div><span className="text-[#7B2FBE]">&gt;</span> Agent-Gamma analyzing local weight gradients...</div>
              <div><span className="text-[#00D4FF]">&gt;</span> Proximity threshold verified. Coordinate synchronization complete.</div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
