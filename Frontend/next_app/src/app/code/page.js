'use client';

import React, { useState } from 'react';
import { 
  Terminal as TermIcon, 
  Play, 
  FileCode, 
  CheckCircle2, 
  AlertTriangle, 
  Activity, 
  FileText,
  Search,
  Check,
  RefreshCw,
  Cpu,
  CornerDownRight
} from 'lucide-react';
import { useStore } from '../../store/useStore';

export default function CodeWorkspacePage() {
  const codeFiles = useStore(state => state.codeFiles);
  const codeLogs = useStore(state => state.codeLogs);
  const addCodeLog = useStore(state => state.addCodeLog);

  const [selectedFile, setSelectedFile] = useState('cognition.py');
  const [runningCmd, setRunningCmd] = useState(false);
  const [terminalInput, setTerminalInput] = useState('');
  
  // Custom analysis metrics saved locally
  const [metrics, setMetrics] = useState({
    qualityScore: 92,
    syntaxValid: true,
    avgComplexity: 3.4,
    docRatio: 0.85,
    totalLines: 124,
    issues: [
      { code: 'F401', message: '`os` imported but unused', line: 12 },
      { code: 'W292', message: 'no newline at end of file', line: 59 }
    ]
  });

  const runAnalysis = async (filename) => {
    setRunningCmd(true);
    addCodeLog(`$ antigravity analyze --file ${filename}`);
    
    // Simulate AST analysis steps in terminal output
    setTimeout(() => addCodeLog(`[INFO] Parsing AST tree for ${filename}...`), 400);
    setTimeout(() => addCodeLog(`[INFO] Walking AST nodes... Found 2 class definitions, 8 functions.`), 800);
    setTimeout(() => addCodeLog(`[INFO] Calculating McCabe cyclomatic complexity: avg = 3.4`), 1200);

    setTimeout(() => {
      setMetrics({
        qualityScore: filename === 'backup1.py' ? 95 : 88,
        syntaxValid: true,
        avgComplexity: filename === 'backup1.py' ? 2.1 : 3.8,
        docRatio: filename === 'app.py' ? 0.72 : 0.90,
        totalLines: filename === 'app.py' ? 552 : 145,
        issues: filename === 'backup1.py' ? [] : [
          { code: 'F401', message: '`json` imported but unused', line: 8 },
          { code: 'E501', message: 'line too long (92 > 79 characters)', line: 44 }
        ]
      });
      addCodeLog(`[SUCCESS] Analysis complete. Quality Score: ${filename === 'backup1.py' ? 95 : 88}/100.`);
      setRunningCmd(false);
    }, 1800);
  };

  const runLint = async () => {
    setRunningCmd(true);
    addCodeLog(`$ antigravity run-lint --all`);
    setTimeout(() => addCodeLog(`[RUFF] Running local linter on all workspace components...`), 500);
    setTimeout(() => {
      addCodeLog(`[RUFF] app.py: L44 E501 line too long`);
      addCodeLog(`[RUFF] cognition.py: L12 F401 'os' imported but unused`);
      addCodeLog(`[SUCCESS] Diagnostics complete. Found 2 warnings.`);
      setRunningCmd(false);
    }, 1500);
  };

  const handleCommandSubmit = (e) => {
    e.preventDefault();
    if (!terminalInput.trim()) return;

    const cmd = terminalInput.trim();
    addCodeLog(`$ ${cmd}`);
    setTerminalInput('');

    if (cmd === 'clear') {
      // Empty logs
      return;
    }

    setRunningCmd(true);
    setTimeout(() => {
      if (cmd.startsWith('help')) {
        addCodeLog(`Available commands:`);
        addCodeLog(`  help                   - Display help context`);
        addCodeLog(`  analyze --file <name>  - Execute AST diagnostics on file`);
        addCodeLog(`  lint                   - Run Ruff checks on python scripts`);
        addCodeLog(`  metrics                - Output active codebase stats`);
      } else if (cmd.startsWith('analyze')) {
        const parts = cmd.split(' ');
        const fileIdx = parts.indexOf('--file');
        const target = fileIdx !== -1 && parts[fileIdx+1] ? parts[fileIdx+1] : 'cognition.py';
        addCodeLog(`[INFO] Querying AST metrics for ${target}...`);
        runAnalysis(target);
      } else if (cmd === 'lint') {
        runLint();
      } else if (cmd === 'metrics') {
        addCodeLog(`Codebase metrics:`);
        addCodeLog(`  Total files: ${codeFiles.length}`);
        addCodeLog(`  Avg Complexity: ${metrics.avgComplexity}`);
        addCodeLog(`  Global Doc Ratio: ${(metrics.docRatio * 100).toFixed(0)}%`);
      } else {
        addCodeLog(`Command not recognized: "${cmd}". Type "help" for instructions.`);
      }
      setRunningCmd(false);
    }, 600);
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
          LOCAL CLAUDE CODE WORKSPACE
        </h1>
        <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
          Perform autonomous AST diagnostics, compute McCabe cyclomatic complexity, and execute Ruff check routines.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Sidebar file tree + metrics */}
        <div className="lg:col-span-1 space-y-6">
          
          {/* File browser */}
          <div className="glass-panel rounded-xl p-4 space-y-3">
            <div className="text-[10px] font-mono text-[#E8EEFF]/40 border-b border-white/5 pb-2 uppercase tracking-wider">
              Workspace Files
            </div>

            <div className="space-y-1">
              {codeFiles.map((file, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedFile(file.name)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg font-mono text-xs transition-all ${
                    selectedFile === file.name 
                      ? 'bg-[#00D4FF]/10 text-[#00D4FF] border border-[#00D4FF]/20' 
                      : 'text-[#E8EEFF]/60 hover:text-white hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <FileCode className="w-3.5 h-3.5" />
                    {file.name}
                  </span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                    file.status === 'healed'
                      ? 'bg-[#22D3A0]/10 text-[#22D3A0]'
                      : 'bg-white/5 text-[#E8EEFF]/40'
                  }`}>
                    {file.status}
                  </span>
                </button>
              ))}
            </div>

            <div className="pt-2">
              <button 
                onClick={() => runAnalysis(selectedFile)}
                disabled={runningCmd}
                className="w-full py-2 bg-[#00D4FF]/10 hover:bg-[#00D4FF]/20 border border-[#00D4FF]/30 text-[#00D4FF] font-mono font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
              >
                <Activity className="w-3.5 h-3.5" />
                ANALYZE SELECTED
              </button>
            </div>
          </div>

          {/* AST summary panel */}
          <div className="glass-panel rounded-xl p-4 space-y-3 font-mono">
            <div className="text-[10px] text-[#E8EEFF]/40 border-b border-white/5 pb-2 uppercase tracking-wider">
              AST Quality Report ({selectedFile})
            </div>

            <div className="space-y-2 text-[11px]">
              <div className="flex justify-between">
                <span className="text-[#E8EEFF]/55">QUALITY SCORE</span>
                <span className={`font-bold ${metrics.qualityScore > 90 ? 'text-[#22D3A0]' : 'text-[#FFB800]'}`}>
                  {metrics.qualityScore}/100
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#E8EEFF]/55">SYNTAX</span>
                <span className="text-[#22D3A0] flex items-center gap-1 font-bold">
                  <CheckCircle2 className="w-3 h-3" /> VALID
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#E8EEFF]/55">AVG COMPLEXITY</span>
                <span className="text-white font-bold">{metrics.avgComplexity}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#E8EEFF]/55">DOCSTRING RATIO</span>
                <span className="text-white font-bold">{(metrics.docRatio * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#E8EEFF]/55">FILE LENGTH</span>
                <span className="text-white font-bold">{metrics.totalLines} lines</span>
              </div>
            </div>
          </div>

        </div>

        {/* Console view & issues */}
        <div className="lg:col-span-3 space-y-6">
          
          {/* Terminal Screen */}
          <div className="glass-panel rounded-xl flex flex-col h-[320px] bg-black/45 border-white/5 overflow-hidden">
            {/* Terminal Top bar */}
            <div className="h-9 bg-black/60 border-b border-white/5 px-4 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[#FF5F56]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#FFBD2E]" />
                <div className="w-2.5 h-2.5 rounded-full bg-[#27C93F]" />
                <span className="font-mono text-[10px] text-[#E8EEFF]/40 ml-2">antigravity@vibhu-oska:~/workspace</span>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={runLint} 
                  disabled={runningCmd}
                  className="font-mono text-[9px] hover:text-[#00D4FF] transition-colors bg-white/5 px-2 py-0.5 rounded border border-white/5 disabled:opacity-50"
                >
                  RUN LINT
                </button>
              </div>
            </div>

            {/* Terminal logs list */}
            <div className="flex-1 p-4 font-mono text-[11px] text-white/80 overflow-y-auto space-y-1.5 select-text">
              {codeLogs.map((log, idx) => (
                <div key={idx} className="whitespace-pre-wrap leading-relaxed">
                  {log.startsWith('$') ? (
                    <span className="text-[#00D4FF] font-bold">{log}</span>
                  ) : log.startsWith('[SUCCESS]') ? (
                    <span className="text-[#22D3A0]">{log}</span>
                  ) : log.startsWith('[RUFF]') ? (
                    <span className="text-[#FFB800]">{log}</span>
                  ) : (
                    <span>{log}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Terminal CLI prompt entry */}
            <form onSubmit={handleCommandSubmit} className="h-10 bg-black/70 border-t border-white/5 flex items-center px-4 shrink-0">
              <CornerDownRight className="w-3.5 h-3.5 text-[#00D4FF] mr-2" />
              <input 
                type="text" 
                value={terminalInput}
                onChange={(e) => setTerminalInput(e.target.value)}
                placeholder="antigravity command (type 'help' for instructions)..."
                className="flex-1 bg-transparent border-none outline-none font-mono text-[11px] text-white placeholder-white/20"
                disabled={runningCmd}
              />
            </form>
          </div>

          {/* Diagnostics warning panel */}
          <div className="glass-panel rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-[#FFB800]" />
                <span className="font-mono text-xs font-bold uppercase tracking-wider">Active Diagnostics Warnings</span>
              </div>
              <span className="font-mono text-[10px] bg-[#FFB800]/10 text-[#FFB800] px-2 py-0.5 rounded">
                {metrics.issues.length} ISSUE(S)
              </span>
            </div>

            {metrics.issues.length === 0 ? (
              <div className="flex items-center justify-center py-6 gap-2 font-mono text-xs text-[#22D3A0]">
                <Check className="w-4 h-4" />
                AST matches complete compliance. Zero lint warnings detected!
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {metrics.issues.map((issue, idx) => (
                  <div key={idx} className="py-2.5 flex justify-between items-center text-xs font-mono">
                    <div className="flex items-center gap-3">
                      <span className="text-[#FFB800] font-bold">[{issue.code}]</span>
                      <span className="text-white/80">{issue.message}</span>
                    </div>
                    <span className="text-[#E8EEFF]/40">Line {issue.line}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
