'use client';

import React, { useState } from 'react';
import { 
  ShieldAlert, 
  Play, 
  Terminal as TermIcon, 
  CheckCircle2, 
  XCircle, 
  Activity, 
  RotateCcw,
  Sparkles,
  Loader2,
  FileSpreadsheet
} from 'lucide-react';
import { useStore } from '../../store/useStore';

export default function SelfUpdaterAdminPage() {
  const updaterStatus = useStore(state => state.updaterStatus);
  const updaterLogs = useStore(state => state.updaterLogs);
  const setUpdater = useStore(state => state.setUpdater);
  const addUpdaterLog = useStore(state => state.addUpdaterLog);

  const [testPath, setTestPath] = useState('Tests/test_brain_stem.py');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const handleTriggerUpdate = async (e) => {
    e.preventDefault();
    setRunning(true);
    setResult(null);
    setUpdater('testing', ['Initializing autonomous self-healing test check...']);
    
    // Simulate pipeline updates in logs
    setTimeout(() => addUpdaterLog(`[TESTING] Executing local command: pytest ${testPath} --tb=short`), 600);

    try {
      const resp = await fetch(`http://127.0.0.1:8000/api/v1/self-update?test_path=${encodeURIComponent(testPath)}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });

      if (!resp.ok) {
        throw new Error('Self-update API call failed');
      }

      const data = await resp.json();
      
      if (data.healed) {
        setTimeout(() => {
          setUpdater('patching', ['[HEALING] Test failures detected in core module.', '[HEALING] Analyzing file syntax trees and AST targets...', ...updaterLogs]);
        }, 1200);

        setTimeout(() => {
          setUpdater('verification', [`[PATCHED] Applied patch: ${data.patch_applied}`, '[VERIFICATION] Re-running unit tests for confirmations...', ...updaterLogs]);
        }, 2200);

        setTimeout(() => {
          setUpdater('idle', [`[SUCCESS] ${data.message}`, ...updaterLogs]);
          setResult(data);
          setRunning(false);
        }, 3400);
      } else {
        setTimeout(() => {
          setUpdater('idle', [`[SUCCESS] ${data.message}`, ...updaterLogs]);
          setResult(data);
          setRunning(false);
        }, 1800);
      }

    } catch (err) {
      console.error(err);
      setUpdater('idle', ['[ERROR] Self-updater link failed. Check backend entry logs.', ...updaterLogs]);
      setResult({
        success: false,
        message: 'Ensure the API Gateway is running on port 8000.',
        test_output: 'pytest run aborted: ConnectionRefusedError'
      });
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
          SELF-UPDATER ENGINE
        </h1>
        <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
          Perform autonomous closed-loop self-correction. Runs unit tests, extracts errors, and applies patches in-place.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Run settings / status bar */}
        <div className="lg:col-span-1 space-y-6">
          
          {/* Settings panel */}
          <div className="glass-panel rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 border-b border-white/5 pb-3">
              <ShieldAlert className="w-4 h-4 text-[#FF4444]" />
              <span className="font-mono text-sm font-bold text-white">Self-Correction Control</span>
            </div>

            <form onSubmit={handleTriggerUpdate} className="space-y-4 font-mono">
              <div className="space-y-1.5">
                <label className="text-[10px] text-[#E8EEFF]/55 uppercase">Target Unit Test</label>
                <input 
                  type="text" 
                  value={testPath} 
                  onChange={(e) => setTestPath(e.target.value)} 
                  placeholder="Tests/test_brain_stem.py"
                  className="w-full bg-[#060912] border border-[#00D4FF]/10 focus:border-[#00D4FF]/30 rounded-lg p-2.5 text-xs text-white outline-none"
                  disabled={running}
                />
              </div>

              <button 
                type="submit"
                disabled={running}
                className="w-full py-2.5 bg-[#FF4444]/10 hover:bg-[#FF4444]/20 border border-[#FF4444]/30 text-[#FF4444] font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
              >
                {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                {running ? 'RUNNING LOOP...' : 'TRIGGER HEALING LOOP'}
              </button>
            </form>
          </div>

          {/* Core state status indicator */}
          <div className="glass-panel rounded-xl p-5 space-y-3 font-mono">
            <div className="text-[10px] text-[#E8EEFF]/40 border-b border-white/5 pb-2 uppercase tracking-wider">
              Self-Healer State
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${
                  updaterStatus === 'idle' ? 'bg-[#22D3A0]' : 'bg-[#FFB800] animate-pulse'
                }`} />
                <span className="text-xs font-bold uppercase">{updaterStatus.toUpperCase()}</span>
              </div>

              <div className="text-[9px] text-[#E8EEFF]/40 leading-relaxed">
                State transitions: <br/>
                <span className={updaterStatus === 'testing' ? 'text-[#00D4FF] font-bold' : ''}>1. TESTING</span> →{' '}
                <span className={updaterStatus === 'patching' ? 'text-[#00D4FF] font-bold' : ''}>2. PATCHING</span> →{' '}
                <span className={updaterStatus === 'verification' ? 'text-[#00D4FF] font-bold' : ''}>3. VERIFICATION</span>
              </div>
            </div>
          </div>

        </div>

        {/* Live healing outputs / test logs */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Log events view */}
          <div className="glass-panel rounded-xl p-5 flex flex-col h-[280px]">
            <div className="flex items-center gap-2 font-mono text-xs text-[#E8EEFF]/55 mb-4 uppercase">
              <TermIcon className="w-3.5 h-3.5" />
              <span>Self-Updater Engine Logs</span>
            </div>
            
            <div className="flex-1 bg-black/45 border border-white/5 rounded-lg p-3 font-mono text-[10px] text-[#E8EEFF]/70 overflow-y-auto space-y-1.5 select-text">
              {updaterLogs.length === 0 ? (
                <div className="text-white/20 italic">Standby. Trigger healing loop to view active test logs.</div>
              ) : (
                updaterLogs.map((log, idx) => (
                  <div key={idx} className="border-b border-white/[0.02] pb-1">
                    <span className="text-[#FF4444]/60">&gt;&gt;</span> {log}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Diagnostic Healing result detail */}
          {result && (
            <div className="glass-panel rounded-xl p-5 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="font-bold uppercase tracking-wider text-white">Diagnostic Results</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  result.success ? 'bg-[#22D3A0]/10 text-[#22D3A0]' : 'bg-[#FF4444]/10 text-[#FF4444]'
                }`}>
                  {result.success ? 'COMPLETED' : 'FAILED'}
                </span>
              </div>

              <div className="space-y-2 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-[#E8EEFF]/40">HEALING APPLIED:</span>
                  <span className="text-white font-bold">{result.healed ? 'YES' : 'NO (ALL PASSED)'}</span>
                </div>
                {result.healed && (
                  <>
                    <div className="flex flex-col gap-1">
                      <span className="text-[#E8EEFF]/40">ERRORS DETECTED:</span>
                      <div className="bg-[#FF4444]/5 border border-[#FF4444]/10 rounded p-2 text-[#FF4444] text-[9px] whitespace-pre-wrap leading-normal font-mono">
                        {result.errors_fixed.map((err, idx) => (
                          <div key={idx}>{err}</div>
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#E8EEFF]/40">PATCH DETAILS:</span>
                      <span className="text-[#00D4FF] font-bold">{result.patch_applied}</span>
                    </div>
                  </>
                )}
              </div>

              {/* Pytest Output */}
              <div className="space-y-1">
                <span className="text-[10px] text-[#E8EEFF]/40 uppercase">Raw Pytest Standard Output</span>
                <pre className="bg-black/55 border border-white/5 rounded-lg p-3 text-[9px] text-[#E8EEFF]/65 overflow-x-auto font-mono max-h-[140px] leading-normal">
                  {result.test_output || 'No test output recorded.'}
                </pre>
              </div>

            </div>
          )}

        </div>

      </div>

    </div>
  );
}
