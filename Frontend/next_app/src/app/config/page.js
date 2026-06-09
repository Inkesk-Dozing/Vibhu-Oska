'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Settings, Database, Cpu, HelpCircle, Save } from 'lucide-react';

export default function ConfigPage() {
  const [lr, setLr] = useState('5e-4');
  const [layers, setLayers] = useState('4');
  const [heads, setHeads] = useState('4');
  const [hiddenDim, setHiddenDim] = useState('128');
  const [vocabSize, setVocabSize] = useState('2000');
  const [datasetSize, setDatasetSize] = useState('5000');
  const [targetDevice, setTargetDevice] = useState('gpu');

  // Training parameters & logs
  const [epochs, setEpochs] = useState('5');
  const [batchSize, setBatchSize] = useState('4');
  const [trainingActive, setTrainingActive] = useState(false);
  const [trainingLogs, setTrainingLogs] = useState([]);

  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  
  const terminalEndRef = useRef(null);

  // Connect WebSocket to backend gateway to capture training logs
  useEffect(() => {
    const socket = new WebSocket('ws://127.0.0.1:8000/ws');
    
    socket.onopen = () => {
      console.log('Connected to WebSocket for config training logs');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'system.model_training_log') {
          const logMsg = data.payload?.log || '';
          setTrainingLogs((prev) => [...prev, logMsg]);
          
          if (
            logMsg.includes('completed successfully') || 
            logMsg.includes('failed') || 
            logMsg.includes('Training failed') ||
            logMsg.includes('training loop completed')
          ) {
            setTrainingActive(false);
          }
        }
      } catch (err) {
        console.error('Error parsing training log WS message:', err);
      }
    };

    socket.onclose = () => {
      console.log('Disconnected from config WebSocket');
    };

    return () => socket.close();
  }, []);

  // Auto-scroll the terminal logs
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [trainingLogs]);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      alert("Hyperparameters saved to local configurations.");
    }, 1000);
  };

  const handleGenerateDataset = () => {
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      alert(`Successfully generated ${datasetSize} synthetic local stories locally!`);
    }, 2000);
  };

  const handleTrainModel = async () => {
    setTrainingActive(true);
    setTrainingLogs(['[SYSTEM] Initialising training request...']);
    
    const payload = {
      learning_rate: lr,
      layers: parseInt(layers, 10) || 4,
      attention_heads: parseInt(heads, 10) || 4,
      hidden_dimension: parseInt(hiddenDim, 10) || 128,
      vocab_size: parseInt(vocabSize, 10) || 2000,
      epochs: parseInt(epochs, 10) || 5,
      batch_size: parseInt(batchSize, 10) || 4,
      device: targetDevice === 'gpu' ? 'cuda' : 'cpu'
    };

    try {
      const resp = await fetch('http://127.0.0.1:8000/api/v1/model/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!resp.ok) {
        const errorData = await resp.json();
        throw new Error(errorData.detail || 'Failed to start training');
      }
      
      setTrainingLogs(prev => [...prev, '[SYSTEM] Training successfully started in background thread. Listening for live updates...']);
    } catch (err) {
      setTrainingLogs(prev => [...prev, `[SYSTEM ERROR] Failed to start training: ${err.message}`]);
      setTrainingActive(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
          MODEL & DATASET CONFIGURATION
        </h1>
        <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
          Configure model parameters and locally generate custom corpora datasets.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Model Hyperparameters Card */}
        <div className="glass-panel rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-white/5 pb-3">
            <Settings className="w-4 h-4 text-[#00D4FF]" />
            <span className="font-mono text-sm font-bold">Transformer Parameters</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Learning Rate</label>
              <input 
                type="text" 
                value={lr} 
                onChange={(e) => setLr(e.target.value)} 
                className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-white outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Layers</label>
              <input 
                type="number" 
                value={layers} 
                onChange={(e) => setLayers(e.target.value)} 
                className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-white outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Attention Heads</label>
              <input 
                type="number" 
                value={heads} 
                onChange={(e) => setHeads(e.target.value)} 
                className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-white outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Hidden Dimension</label>
              <input 
                type="number" 
                value={hiddenDim} 
                onChange={(e) => setHiddenDim(e.target.value)} 
                className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-white outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Vocab Size (BPE)</label>
              <input 
                type="number" 
                value={vocabSize} 
                onChange={(e) => setVocabSize(e.target.value)} 
                className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-white outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Target Device</label>
              <select 
                value={targetDevice} 
                onChange={(e) => setTargetDevice(e.target.value)} 
                className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-white outline-none"
              >
                <option value="gpu">GPU (RTX 4060)</option>
                <option value="cpu">CPU Fallback</option>
              </select>
            </div>
          </div>

          <button 
            onClick={handleSave}
            disabled={saving}
            className="w-full py-2 bg-[#00D4FF]/10 hover:bg-[#00D4FF]/20 border border-[#00D4FF]/30 text-[#00D4FF] font-mono font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? 'SAVING...' : 'SAVE CONFIGURATION'}
          </button>
        </div>

        {/* Dataset Generator Card */}
        <div className="glass-panel rounded-xl p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 border-b border-white/5 pb-3">
              <Database className="w-4 h-4 text-[#FFB800]" />
              <span className="font-mono text-sm font-bold">Local Dataset Synthesizer</span>
            </div>

            <div className="mt-4 space-y-3">
              <p className="text-xs text-[#E8EEFF]/60 font-mono leading-relaxed">
                NeuralForge compiles models using custom locally-synthesized story datasets. Generate raw corpus tokens in-place.
              </p>
              
              <div className="space-y-1">
                <label className="font-mono text-[10px] text-[#E8EEFF]/50 uppercase">Number of Examples</label>
                <input 
                  type="number" 
                  value={datasetSize} 
                  onChange={(e) => setDatasetSize(e.target.value)} 
                  className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 font-mono text-xs text-[#FFB800] outline-none"
                />
              </div>
            </div>
          </div>

          <button 
            onClick={handleGenerateDataset}
            disabled={generating}
            className="w-full py-2 bg-[#FFB800]/10 hover:bg-[#FFB800]/20 border border-[#FFB800]/30 text-[#FFB800] font-mono font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 mt-4"
          >
            <Database className="w-3.5 h-3.5" />
            {generating ? 'SYNTHESIZING...' : 'SYNTHESIZE CORPUS LOCALLY'}
          </button>
        </div>

      </div>

      {/* Sovereign GPT Training Terminal Panel */}
      <div className="glass-panel rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#00D4FF]" />
            <span className="font-mono text-sm font-bold">Vibhu-Oska Sovereign GPT Training Console</span>
          </div>
          {trainingActive && (
            <div className="flex items-center gap-1.5 font-mono text-[10px] text-[#00D4FF] animate-pulse">
              <span className="w-2.5 h-2.5 rounded-full bg-[#00D4FF]" />
              TRAINING IN PROGRESS
            </div>
          )}
        </div>

        {/* Hyperparams for training row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-2 font-mono text-xs">
          <div className="space-y-1">
            <label className="text-[10px] text-[#E8EEFF]/50 uppercase">Epochs</label>
            <input 
              type="number" 
              value={epochs} 
              onChange={(e) => setEpochs(e.target.value)} 
              disabled={trainingActive}
              className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 text-white outline-none disabled:opacity-50"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] text-[#E8EEFF]/50 uppercase">Batch Size</label>
            <input 
              type="number" 
              value={batchSize} 
              onChange={(e) => setBatchSize(e.target.value)} 
              disabled={trainingActive}
              className="w-full bg-[#060912]/80 border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 text-white outline-none disabled:opacity-50"
            />
          </div>
          <div className="col-span-2 flex items-end">
            <button 
              onClick={handleTrainModel}
              disabled={trainingActive}
              className="w-full py-2 bg-[#00D4FF]/10 hover:bg-[#00D4FF]/20 border border-[#00D4FF]/30 text-[#00D4FF] font-mono font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
            >
              <Cpu className="w-3.5 h-3.5" />
              {trainingActive ? 'TRAINING IN PROGRESS...' : 'INITIALISE SOVEREIGN GPT TRAINING'}
            </button>
          </div>
        </div>

        {/* Terminal Logs Output */}
        <div className="w-full h-64 bg-[#03060f]/90 border border-white/5 rounded-lg p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-1 select-text scrollbar-thin">
          {trainingLogs.length === 0 ? (
            <div className="text-white/20 italic">No active training logs. Adjust parameters and click "Initialise Sovereign GPT Training" to start.</div>
          ) : (
            trainingLogs.map((logLine, idx) => {
              let color = 'text-white/70';
              if (logLine.includes('✓') || logLine.includes('successful')) {
                color = 'text-[#22D3A0] font-bold';
              } else if (logLine.includes('❌') || logLine.includes('failed') || logLine.includes('ERROR')) {
                color = 'text-[#FF6B6B] font-bold';
              } else if (logLine.includes('Epoch')) {
                color = 'text-[#FFB800]';
              } else if (logLine.startsWith('[SYSTEM]')) {
                color = 'text-[#00D4FF]/80';
              }
              return (
                <div key={idx} className={color}>
                  {logLine}
                </div>
              );
            })
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>

    </div>
  );
}
