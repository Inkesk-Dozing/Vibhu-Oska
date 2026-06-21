'use client';

import React, { useEffect, useState } from 'react';
import { 
  Play, 
  Square, 
  Terminal as TermIcon, 
  Cpu, 
  TrendingDown, 
  Activity, 
  Zap 
} from 'lucide-react';
import { useStore } from '../store/useStore';

export default function DashboardPage() {
  const training = useStore(state => state.training);
  const startTraining = useStore(state => state.startTraining);
  const stopTraining = useStore(state => state.stopTraining);
  const updateTrainingMetrics = useStore(state => state.updateTrainingMetrics);

  const [activeStep, setActiveStep] = useState(0);

  // Training simulation loop
  useEffect(() => {
    if (!training.active) return;

    const interval = setInterval(() => {
      const nextStep = training.step + 1;
      const progress = nextStep / 100;
      
      // Calculate simulated loss decrement
      const currentLoss = Math.max(1.12, 4.5 - (nextStep * 0.034) + Math.random() * 0.08);
      const currentThroughput = Math.floor(1240 + Math.random() * 180);
      const nextEpoch = Math.floor(nextStep / 10);
      
      const newLog = `Step ${nextStep}/100 - Epoch ${nextEpoch} - Loss: ${currentLoss.toFixed(4)} - Rate: ${currentThroughput} tok/s`;
      
      const newLossHistory = [...training.lossHistory, currentLoss];
      if (newLossHistory.length > 20) newLossHistory.shift();

      updateTrainingMetrics({
        step: nextStep,
        epoch: nextEpoch,
        loss: currentLoss,
        throughput: currentThroughput,
        logs: [newLog, ...training.logs.slice(0, 30)],
        lossHistory: newLossHistory
      });

      if (nextStep >= 100) {
        clearInterval(interval);
        updateTrainingMetrics({ active: false, logs: ['Training complete. Local Model weights exported to registry.', ...training.logs] });
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [training.active, training.step, training.lossHistory, training.logs, updateTrainingMetrics]);

  return (
    <div className="space-y-6">
      
      {/* Title Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
            NEURALFORGE ENGINE
          </h1>
          <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
            Local Transformer Training Dashboard (Ryzen 9 + RTX 4060)
          </p>
        </div>

        {/* Training control buttons */}
        <div className="flex gap-2">
          {!training.active ? (
            <button 
              onClick={startTraining}
              className="px-4 py-2 bg-[#00D4FF] hover:bg-[#00D4FF]/90 text-black font-mono font-bold text-xs rounded-lg flex items-center gap-2 transition-all shadow-md shadow-[#00D4FF]/10 active:scale-95"
            >
              <Play className="w-3.5 h-3.5 fill-black" />
              START LOCAL TRAINING
            </button>
          ) : (
            <button 
              onClick={stopTraining}
              className="px-4 py-2 bg-[#FF4444] hover:bg-[#FF4444]/90 text-white font-mono font-bold text-xs rounded-lg flex items-center gap-2 transition-all shadow-md shadow-[#FF4444]/10 active:scale-95"
            >
              <Square className="w-3.5 h-3.5 fill-white" />
              HALT TRAINING
            </button>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        
        {/* Card: Loss */}
        <div className="glass-panel rounded-xl p-4 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-[#00D4FF]/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center gap-2 text-[#E8EEFF]/40 font-mono text-[10px]">
            <TrendingDown className="w-3.5 h-3.5 text-[#00D4FF]" />
            <span>TRAINING LOSS</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-[#00D4FF]">{training.loss.toFixed(4)}</span>
            {training.active && <span className="text-[10px] text-[#22D3A0] font-mono">-0.034</span>}
          </div>
          <div className="text-[9px] font-mono text-[#E8EEFF]/30 mt-2">Target: &lt; 1.000</div>
        </div>

        {/* Card: Epoch */}
        <div className="glass-panel rounded-xl p-4 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-[#7B2FBE]/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center gap-2 text-[#E8EEFF]/40 font-mono text-[10px]">
            <Activity className="w-3.5 h-3.5 text-[#7B2FBE]" />
            <span>EPOCH / STEP</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold font-mono text-white">
              {training.epoch} <span className="text-xs text-[#E8EEFF]/40">/ {training.step}</span>
            </span>
          </div>
          <div className="text-[9px] font-mono text-[#E8EEFF]/30 mt-2">Max Epochs: {training.maxEpochs}</div>
        </div>

        {/* Card: Token Throughput */}
        <div className="glass-panel rounded-xl p-4 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-[#FFB800]/5 rounded-bl-full pointer-events-none" />
          <div className="flex items-center gap-2 text-[#E8EEFF]/40 font-mono text-[10px]">
            <Zap className="w-3.5 h-3.5 text-[#FFB800]" />
            <span>THROUGHPUT</span>
          </div>
          <div className="mt-2">
            <span className="text-2xl font-bold font-mono text-[#FFB800]">{training.throughput}</span>
            <span className="text-xs text-[#E8EEFF]/40 font-mono ml-1">tok/s</span>
          </div>
          <div className="text-[9px] font-mono text-[#E8EEFF]/30 mt-2">RTX 4060 GPU Target</div>
        </div>

        {/* Card: Training Status */}
        <div className="glass-panel rounded-xl p-4 flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-center gap-2 text-[#E8EEFF]/40 font-mono text-[10px]">
            <Cpu className="w-3.5 h-3.5 text-[#22D3A0]" />
            <span>STATE</span>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <div className={`w-2.5 h-2.5 rounded-full ${training.active ? 'bg-[#22D3A0] animate-pulse shadow-md shadow-[#22D3A0]/30' : 'bg-[#E8EEFF]/20'}`} />
            <span className="text-base font-bold font-mono tracking-wider">
              {training.active ? 'TRAINING' : 'STANDBY'}
            </span>
          </div>
          <div className="text-[9px] font-mono text-[#E8EEFF]/30 mt-2">Sovereign Intel Core</div>
        </div>

      </div>

      {/* Main Grid: Graph + Console */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Loss Curve Graph */}
        <div className="lg:col-span-2 glass-panel rounded-xl p-5 flex flex-col h-[320px]">
          <div className="font-mono text-xs text-[#E8EEFF]/55 mb-4 uppercase">
            Loss Convergence Curve
          </div>
          <div className="flex-1 flex items-end gap-[4px] border-b border-l border-white/5 pb-2 pl-2">
            {training.lossHistory.length === 0 ? (
              <div className="w-full h-full flex items-center justify-center font-mono text-xs text-[#E8EEFF]/25">
                No active training session data
              </div>
            ) : (
              training.lossHistory.map((val, idx) => {
                const heightPct = Math.min(100, (val / 5.0) * 100);
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center justify-end h-full group relative">
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-1 scale-0 group-hover:scale-100 transition-all font-mono text-[9px] bg-[#0A0E1A] border border-[#00D4FF]/25 px-1.5 py-0.5 rounded text-[#00D4FF] z-30">
                      {val.toFixed(3)}
                    </div>
                    {/* Bar */}
                    <div 
                      className="w-full bg-[#00D4FF]/20 border-t border-[#00D4FF] hover:bg-[#00D4FF]/45 transition-colors rounded-t-[2px]" 
                      style={{ height: `${heightPct}%` }}
                    />
                  </div>
                );
              })
            )}
          </div>
          <div className="flex justify-between font-mono text-[9px] text-[#E8EEFF]/30 mt-2">
            <span>START (STEP 0)</span>
            <span>REALTIME CONVERGENCE</span>
            <span>END (STEP 100)</span>
          </div>
        </div>

        {/* Live Training Console Logs */}
        <div className="glass-panel rounded-xl p-5 flex flex-col h-[320px]">
          <div className="flex items-center gap-2 font-mono text-xs text-[#E8EEFF]/55 mb-4 uppercase">
            <TermIcon className="w-3.5 h-3.5" />
            <span>Local Training Logs</span>
          </div>
          <div className="flex-1 bg-black/45 border border-white/5 rounded-lg p-3 font-mono text-[10px] text-[#E8EEFF]/65 overflow-y-auto space-y-1.5">
            {training.logs.length === 0 ? (
              <div className="text-[#E8EEFF]/25 italic">Standby. Core waiting for telemetry activation.</div>
            ) : (
              training.logs.map((log, idx) => (
                <div key={idx} className="border-b border-white/[0.02] pb-1">
                  <span className="text-[#00D4FF]/60">&gt;&gt;</span> {log}
                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
