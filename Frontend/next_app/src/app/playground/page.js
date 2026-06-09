'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Bot, 
  User, 
  Cpu, 
  ChevronDown, 
  ChevronUp, 
  Mic, 
  Lock, 
  Unlock,
  Volume2,
  Trash2,
  BrainCircuit,
  Loader2
} from 'lucide-react';
import { useStore } from '../../store/useStore';

export default function PlaygroundPage() {
  const chatHistory = useStore(state => state.chatHistory);
  const addChatMessage = useStore(state => state.addChatMessage);
  const clearChatHistory = useStore(state => state.clearChatHistory);
  const telemetry = useStore(state => state.telemetry);

  const [input, setInput] = useState('');
  const [model, setModel] = useState('vibhu-core');
  const [temperature, setTemperature] = useState(0.7);
  const [thinkingVisible, setThinkingVisible] = useState({});
  const [ws, setWs] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [pending, setPending] = useState(false);
  const [voiceLockActive, setVoiceLockActive] = useState(false);
  const [voiceCalibrated, setVoiceCalibrated] = useState(false);

  const messagesEndRef = useRef(null);

  const renderMessageContent = (content, role) => {
    if (role !== 'assistant') {
      return content;
    }
    
    // Support single, double, smart quotes, smart spaces, case insensitivity
    const typoRegex = /Aha,\s+I\s+see\s+typo\s+there\s+['"“]([^'”"]+)['"”]\s+and\s+correct\s+is\s+['"“]([^'”"]+)['"”]\.?(.*)/is;
    const match = content.match(typoRegex);
    
    if (match) {
      const incorrect = match[1];
      const correct = match[2];
      const restOfContent = match[3]?.trim();
      
      return (
        <div className="space-y-3">
          {/* Glowing Diagnostic Warning Box */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-[#FFB800]/5 border border-[#FFB800]/25 shadow-[0_0_15px_rgba(255,184,0,0.08)] font-mono text-xs text-[#FFD066]">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#FFB800] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#FFB800]"></span>
            </span>
            <div className="flex-1 text-[11px] leading-relaxed">
              <span className="font-bold text-white uppercase tracking-wider text-[9px] block mb-0.5">Spelling Correction Auto-Logged</span>
              Detected typo <code className="px-1.5 py-0.5 rounded bg-black/45 border border-[#FFB800]/15 text-[#FFB800]">{incorrect}</code>, corrected to <code className="px-1.5 py-0.5 rounded bg-black/45 border border-[#FFB800]/15 text-[#22D3A0]">{correct}</code>.
            </div>
          </div>
          
          {/* Rest of the message content */}
          {restOfContent && (
            <div className="text-white/90 whitespace-pre-wrap">
              {restOfContent}
            </div>
          )}
        </div>
      );
    }
    
    return <div className="whitespace-pre-wrap">{content}</div>;
  };

  // Sync state with localstorage for Voice Lock info
  useEffect(() => {
    const active = localStorage.getItem('creator_voice_lock_active') === 'true';
    const pitch = localStorage.getItem('creator_voice_pitch');
    setVoiceLockActive(active);
    setVoiceCalibrated(!!pitch);
  }, []);

  // Connect WebSocket to backend gateway
  useEffect(() => {
    setConnecting(true);
    const socket = new WebSocket('ws://127.0.0.1:8000/ws');
    
    socket.onopen = () => {
      setConnecting(false);
      console.log('Connected to Vibhu-Oska Gateway WebSocket');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket event received:", data);
        
        // Handle task.completed event
        if (data.type === 'task.completed') {
          const payload = data.payload || {};
          const content = payload.content || '';
          const target = payload.metadata?.executed_on === 'gpu' ? 'GPU' : 'CPU';
          const elapsed = payload.metadata?.processing_time_ms || 0;
          const statusMsg = payload.metadata?.status?.message || 'Done';
          
          const thinkingText = `Synaptic paths completed. Routed on: ${target} in ${elapsed}ms.\nStatus: ${statusMsg}`;

          addChatMessage({
            role: 'assistant',
            content: content,
            thinking: thinkingText
          });
          setPending(false);
        } else if (data.type === 'task.failed') {
          const payload = data.payload || {};
          const error = payload.error || 'Cognition failed';
          addChatMessage({
            role: 'assistant',
            content: `⚠️ Error: ${error}`,
            thinking: 'Execution failure reported by Orchestrator core.'
          });
          setPending(false);
        }
      } catch (err) {
        console.error('Error parsing WS message:', err);
      }
    };

    socket.onclose = () => {
      setConnecting(false);
      console.log('Disconnected from Vibhu-Oska Gateway WebSocket');
    };

    setWs(socket);
    return () => socket.close();
  }, [addChatMessage]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || pending) return;

    const userPrompt = input.trim();
    setInput('');
    setPending(true);

    // Add User message
    addChatMessage({ role: 'user', content: userPrompt });

    // Build the request payload
    const payload = {
      prompt: userPrompt,
      model_id: model,
      temperature: Number(temperature),
      max_tokens: 1024,
      session_id: 'local-playground-session'
    };

    try {
      // Call REST endpoint of gateway for processing
      const resp = await fetch('http://127.0.0.1:8000/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!resp.ok) {
        throw new Error('Gateway response error');
      }

      console.log("Prompt accepted by backend gateway.");
      // The assistant response will be appended when WebSocket receives 'task.completed'
    } catch (err) {
      console.error(err);
      addChatMessage({
        role: 'assistant',
        content: 'Gateway error. Please ensure python -m Backend.EntryPoint is running.',
        thinking: 'WebSocket/HTTP connection failed to route request.'
      });
      setPending(false);
    }
  };

  const toggleThinking = (idx) => {
    setThinkingVisible(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] relative">
      {/* Page Header */}
      <div className="flex justify-between items-center mb-4 shrink-0">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
            SOVEREIGN PLAYGROUND
          </h1>
          <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
            Local Chat Workspace with Sentient Fallback & Voice Lock
          </p>
        </div>

        {/* Status indicator */}
        <div className="flex gap-2">
          <button
            onClick={clearChatHistory}
            className="glass-panel px-3 py-1.5 rounded-lg flex items-center gap-2 font-mono text-[10px] text-[#FF5D5D]/80 hover:text-[#FF5D5D] hover:bg-[#FF5D5D]/10 transition-all border border-transparent hover:border-[#FF5D5D]/20 active:scale-95 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>CLEAR CHAT</span>
          </button>
          <div className="glass-panel px-3 py-1.5 rounded-lg flex items-center gap-2 font-mono text-[10px]">
            <Lock className={`w-3.5 h-3.5 ${voiceLockActive ? 'text-[#00D4FF]' : 'text-white/25'}`} />
            <span className={voiceLockActive ? 'text-[#00D4FF]' : 'text-[#E8EEFF]/55'}>
              VOICE LOCK: {voiceLockActive ? 'SECURED' : 'UNLOCKED'}
            </span>
          </div>
          <div className="glass-panel px-3 py-1.5 rounded-lg flex items-center gap-2 font-mono text-[10px]">
            <div className={`w-2 h-2 rounded-full ${connecting ? 'bg-[#FFB800]' : 'bg-[#22D3A0] animate-pulse'}`} />
            <span className="text-[#E8EEFF]/70">GATEWAY: ONLINE</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Settings sidebar + Chat area */}
      <div className="flex-1 flex gap-6 min-h-0">
        
        {/* Left config column */}
        <div className="w-64 glass-panel rounded-xl p-4 flex flex-col gap-4 shrink-0 font-mono text-xs">
          <div className="text-[10px] text-[#E8EEFF]/40 border-b border-white/5 pb-2 uppercase tracking-wider">
            Inference Parameters
          </div>

          <div className="space-y-1">
            <label className="text-[10px] text-[#E8EEFF]/50 uppercase">Active Model</label>
            <select 
              value={model} 
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-[#060912] border border-[#00D4FF]/10 focus:border-[#00D4FF]/40 rounded-lg p-2 text-white outline-none"
            >
              <option value="vibhu-core">Vibhu-Oska Core (Cognition)</option>
              <option value="sovereign-gpt">Vibhu-Oska Sovereign GPT (From Scratch)</option>
              <option value="backup-1">BackupCore1 (Sentient Failover)</option>
            </select>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-[10px]">
              <span className="text-[#E8EEFF]/50 uppercase">Temperature</span>
              <span className="text-[#00D4FF]">{temperature}</span>
            </div>
            <input 
              type="range" 
              min="0.1" 
              max="1.5" 
              step="0.1" 
              value={temperature} 
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-[#00D4FF] bg-white/5 h-1 rounded-lg outline-none cursor-pointer"
            />
          </div>

          <div className="mt-auto p-3 bg-[#0A0E1A] border border-[#00D4FF]/5 rounded-lg space-y-2">
            <div className="flex items-center gap-2 text-[10px] text-[#00D4FF] font-bold">
              <BrainCircuit className="w-3.5 h-3.5" />
              <span>STRICTLY LOCAL</span>
            </div>
            <p className="text-[9px] text-[#E8EEFF]/40 leading-relaxed">
              No remote packages are sent. Inputs stay safe inside local sandbox, passing via local ZMQ bus loops.
            </p>
          </div>
        </div>

        {/* Right chat message area */}
        <div className="flex-1 glass-panel rounded-xl flex flex-col min-w-0">
          
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatHistory.length <= 1 && (
              <div className="flex flex-col items-center justify-center py-8 px-4 text-center max-w-xl mx-auto space-y-4 font-mono">
                <div className="p-3 bg-[#00D4FF]/5 rounded-full border border-[#00D4FF]/10 text-[#00D4FF] animate-pulse">
                  <BrainCircuit className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">Suggested Diagnostic Prompts</h3>
                  <p className="text-[10px] text-[#E8EEFF]/40">Select a prompt template below to execute local model inference and verify semantic correctness.</p>
                </div>
                <div className="grid grid-cols-2 gap-2 w-full pt-2">
                  <button 
                    type="button"
                    onClick={() => setInput("wtf is this now sihg")}
                    className="p-2.5 rounded-lg bg-[#0C1222]/80 border border-[#FFB800]/10 hover:border-[#FFB800]/30 hover:bg-[#FFB800]/5 transition-all text-left group active:scale-98 cursor-pointer"
                  >
                    <div className="text-[9px] text-[#FFB800] uppercase font-bold tracking-wider mb-1">Typo Logging Check</div>
                    <div className="text-[10px] text-white/70 group-hover:text-white transition-colors truncate">"wtf is this now sihg"</div>
                  </button>
                  <button 
                    type="button"
                    onClick={() => setInput("spell cognitive")}
                    className="p-2.5 rounded-lg bg-[#0C1222]/80 border border-[#00D4FF]/10 hover:border-[#00D4FF]/30 hover:bg-[#00D4FF]/5 transition-all text-left group active:scale-98 cursor-pointer"
                  >
                    <div className="text-[9px] text-[#00D4FF] uppercase font-bold tracking-wider mb-1">Letters & Spelling</div>
                    <div className="text-[10px] text-white/70 group-hover:text-white transition-colors truncate">"spell cognitive"</div>
                  </button>
                  <button 
                    type="button"
                    onClick={() => setInput("what is 5 times 5?")}
                    className="p-2.5 rounded-lg bg-[#0C1222]/80 border border-[#22D3A0]/10 hover:border-[#22D3A0]/30 hover:bg-[#22D3A0]/5 transition-all text-left group active:scale-98 cursor-pointer"
                  >
                    <div className="text-[9px] text-[#22D3A0] uppercase font-bold tracking-wider mb-1">Arithmetic Math</div>
                    <div className="text-[10px] text-white/70 group-hover:text-white transition-colors truncate">"what is 5 times 5?"</div>
                  </button>
                  <button 
                    type="button"
                    onClick={() => setInput("write a react functional component")}
                    className="p-2.5 rounded-lg bg-[#0C1222]/80 border border-[#7B2FBE]/10 hover:border-[#7B2FBE]/30 hover:bg-[#7B2FBE]/5 transition-all text-left group active:scale-98 cursor-pointer"
                  >
                    <div className="text-[9px] text-[#D2A0FF] uppercase font-bold tracking-wider mb-1">Coding Logic</div>
                    <div className="text-[10px] text-white/70 group-hover:text-white transition-colors truncate">"write a react functional component"</div>
                  </button>
                </div>
              </div>
            )}

            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
                
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  msg.role === 'user' 
                    ? 'bg-[#7B2FBE]/20 border border-[#7B2FBE]/30 text-[#D2A0FF]' 
                    : 'bg-[#00D4FF]/10 border border-[#00D4FF]/25 text-[#00D4FF]'
                }`}>
                  {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Content */}
                <div className="space-y-1">
                  
                  {/* Thinking Section for assistant */}
                  {msg.role === 'assistant' && msg.thinking && (
                    <div className="border border-[#00D4FF]/10 rounded-lg bg-[#040814]/85 font-mono text-[10px] overflow-hidden shadow-inner shadow-black/80">
                      <button 
                        onClick={() => toggleThinking(idx)}
                        className="w-full px-3 py-2 flex justify-between items-center bg-gradient-to-r from-[#00D4FF]/5 to-transparent text-[#00D4FF]/70 hover:text-[#00D4FF] transition-colors"
                      >
                        <span className="flex items-center gap-2 tracking-widest text-[9px] uppercase">
                          <BrainCircuit className="w-3.5 h-3.5 text-[#00D4FF] animate-pulse" />
                          Synaptic Tracer Output
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-[#22D3A0] animate-ping" />
                          <span className="text-[8px] text-[#22D3A0]/80">DIAG_OK</span>
                          {thinkingVisible[idx] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </div>
                      </button>
                      
                      {thinkingVisible[idx] && (
                        <div className="p-3.5 border-t border-[#00D4FF]/10 text-[#E8EEFF]/70 leading-relaxed whitespace-pre-line bg-black/40 font-mono text-[9px] border-l-2 border-l-[#00D4FF]/40">
                          <div className="text-[#00D4FF]/40 mb-2 border-b border-[#00D4FF]/5 pb-1 font-bold text-[8px] tracking-wider uppercase flex justify-between">
                            <span>Console Logs // Relational & Neural Inference Path</span>
                            <span className="animate-pulse">ONLINE</span>
                          </div>
                          <div className="space-y-1 text-white/80">
                            {msg.thinking.split('\n').map((line, lIdx) => (
                              <div key={lIdx} className="flex gap-2">
                                <span className="text-[#00D4FF]/50">&gt;</span>
                                <span>{line}</span>
                              </div>
                            ))}
                            <div className="flex items-center gap-1 text-[#22D3A0]/60">
                              <span className="text-[#22D3A0]">&gt;</span>
                              <span>Trace collapse complete. Superposition resolved.</span>
                              <span className="h-3 w-1.5 bg-[#22D3A0] animate-pulse ml-0.5 inline-block align-middle" />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actual Text Bubble */}
                  <div className={`rounded-xl px-4 py-2.5 text-xs font-sans leading-relaxed ${
                    msg.role === 'user' 
                      ? 'bg-gradient-to-br from-[#7B2FBE]/15 to-[#7B2FBE]/5 border border-[#7B2FBE]/20 shadow-md shadow-[#7B2FBE]/5 text-white' 
                      : 'bg-[#0C1222]/90 border border-[#00D4FF]/10 shadow-lg shadow-black/40 text-white/90'
                  }`}>
                    {renderMessageContent(msg.content, msg.role)}
                  </div>

                </div>

              </div>
            ))}
            {pending && (
              <div className="flex gap-3 max-w-[85%]">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 bg-[#00D4FF]/10 border border-[#00D4FF]/25 text-[#00D4FF]">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="space-y-1">
                  <div className="rounded-xl px-4 py-2.5 text-xs font-sans leading-relaxed bg-[#0A0E1A] border border-[#00D4FF]/10 text-white/50 flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#00D4FF]" />
                    Vibhu-Oska is thinking...
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Chat Box Form */}
          <form onSubmit={handleSend} className="p-4 border-t border-white/5 bg-black/15 flex gap-2">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={voiceLockActive ? "Speak to type (locked to creator's signature) or type securely..." : "Type your query here..."}
              className="flex-1 bg-[#060912] border border-[#00D4FF]/10 focus:border-[#00D4FF]/30 rounded-xl px-4 py-3 font-mono text-xs text-white outline-none placeholder-white/20"
            />
            
            <button 
              type="submit"
              className="px-5 bg-[#00D4FF] hover:bg-[#00D4FF]/90 text-black font-bold rounded-xl flex items-center justify-center transition-all active:scale-95 shadow-md shadow-[#00D4FF]/10"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

        </div>

      </div>

    </div>
  );
}
