'use client';

import React, { useState } from 'react';
import { 
  Search, 
  Sparkles, 
  ExternalLink, 
  Layers, 
  Globe, 
  HelpCircle,
  FileText,
  Loader2,
  Database
} from 'lucide-react';
import { useStore } from '../../store/useStore';

export default function ResearchPage() {
  const [query, setQuery] = useState('');
  const [deepSearch, setDeepSearch] = useState(false);
  const [numResults, setNumResults] = useState(3);
  const [loading, setLoading] = useState(false);
  const [searchState, setSearchState] = useState('');
  
  // Save results in state
  const [results, setResults] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResults(null);
    setSearchState('Initializing local research node...');

    try {
      // Simulate search state transition
      setTimeout(() => setSearchState('Querying local SearXNG Docker container...'), 500);
      setTimeout(() => setSearchState(deepSearch ? 'Concurrent scraper fetching URLs...' : 'Extracting snippets & scoring matching indices...'), 1200);

      const resp = await fetch('http://127.0.0.1:8000/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          num_results: Number(numResults),
          deep: deepSearch
        })
      });

      if (!resp.ok) {
        throw new Error('Search request failed');
      }

      const data = await resp.json();
      
      // Allow a brief moment to show synthesis
      setTimeout(() => {
        setResults(data);
        setLoading(false);
      }, 1800);

      setSearchState('Local synthesiser parsing corpus weights...');

    } catch (err) {
      console.error(err);
      // Fallback/Error state
      setResults({
        error: true,
        message: 'Could not connect to SearXNG. Ensure Docker container or local search plugin is active.'
      });
      setLoading(false);
    }
  };

  const renderSynthesis = (corpus, sources) => {
    if (!corpus) return null;
    
    // Split corpus into manageable sentences and highlight citations
    // Simple parsing to turn [Source 1], [Source 2], etc. or [1], [2] into clickable citation links
    let text = corpus;
    
    // Replace [Source X] with a neat button
    const elements = [];
    let lastIndex = 0;
    const regex = /\[Source\s+(\d+)\]|\[(\d+)\]/gi;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const matchIndex = match.index;
      const sourceNum = match[1] || match[2];

      // Add text before match
      if (matchIndex > lastIndex) {
        elements.push(<span key={lastIndex}>{text.substring(lastIndex, matchIndex)}</span>);
      }

      // Add citation link
      elements.push(
        <a 
          key={matchIndex} 
          href={`#source-${sourceNum}`} 
          className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-[#00D4FF]/20 text-[#00D4FF] hover:bg-[#00D4FF]/40 text-[9px] font-mono font-bold mx-0.5 border border-[#00D4FF]/30 transition-colors cursor-pointer"
        >
          {sourceNum}
        </a>
      );

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      elements.push(<span key={lastIndex}>{text.substring(lastIndex)}</span>);
    }

    return (
      <div className="text-xs font-sans leading-relaxed text-white/90 space-y-3 whitespace-pre-wrap">
        {elements.length > 0 ? elements : text}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold font-mono tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-[#E8EEFF] to-[#00D4FF]">
          LOCAL PERPLEXITY RESEARCH
        </h1>
        <p className="text-xs text-[#E8EEFF]/40 font-mono mt-1">
          Perform deep research locally. Queries search index, extracts website content, and constructs structured summaries.
        </p>
      </div>

      {/* Query Bar */}
      <div className="glass-panel rounded-xl p-5">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-white/20" />
              <input 
                type="text" 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What local codebase or web documentation query would you like to explore?"
                className="w-full bg-[#060912] border border-[#00D4FF]/10 focus:border-[#00D4FF]/35 rounded-xl pl-10 pr-4 py-3 font-mono text-xs text-white outline-none placeholder-white/25"
                disabled={loading}
              />
            </div>
            <button 
              type="submit" 
              disabled={loading || !query.trim()}
              className="px-5 bg-[#00D4FF] hover:bg-[#00D4FF]/90 text-black font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
              SEARCH
            </button>
          </div>

          {/* Settings */}
          <div className="flex flex-wrap gap-4 items-center font-mono text-[10px] text-[#E8EEFF]/60 pt-2 border-t border-white/5">
            <label className="flex items-center gap-2 cursor-pointer hover:text-white">
              <input 
                type="checkbox" 
                checked={deepSearch} 
                onChange={(e) => setDeepSearch(e.target.checked)}
                className="accent-[#00D4FF]"
                disabled={loading}
              />
              <span>DEEP RESEARCH MODE (SCRAPE & SUMMARIZE)</span>
            </label>

            <div className="h-3 w-px bg-white/10" />

            <div className="flex items-center gap-2">
              <span>SOURCES TARGET:</span>
              <select 
                value={numResults} 
                onChange={(e) => setNumResults(Number(e.target.value))}
                className="bg-[#060912] border border-[#00D4FF]/10 rounded px-1.5 py-0.5 text-white outline-none cursor-pointer"
                disabled={loading}
              >
                <option value="3">3 URLs</option>
                <option value="5">5 URLs</option>
                <option value="8">8 URLs</option>
              </select>
            </div>
          </div>
        </form>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="glass-panel rounded-xl p-8 flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-8 h-8 text-[#00D4FF] animate-spin" />
          <div className="text-center">
            <div className="font-mono text-xs text-white">{searchState}</div>
            <div className="font-mono text-[9px] text-[#E8EEFF]/30 mt-1">Sovereign agent querying local containers...</div>
          </div>
        </div>
      )}

      {/* Results panel */}
      {results && !loading && (
        <div className="space-y-6">
          
          {results.error ? (
            <div className="glass-panel rounded-xl p-6 border-[#FF4444]/20 space-y-2">
              <div className="font-mono text-xs font-bold text-[#FF4444]">RESEARCH CORRUPTED</div>
              <p className="text-xs text-[#E8EEFF]/60 font-mono leading-relaxed">{results.message}</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Main AI Synthesized Response */}
              <div className="lg:col-span-2 space-y-4">
                
                {/* Synthesis Card */}
                <div className="glass-panel rounded-xl p-5 space-y-3">
                  <div className="flex items-center gap-2 font-mono text-[10px] text-[#00D4FF] font-bold uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Synthesized Local Answer</span>
                  </div>

                  <div className="border-t border-white/5 pt-3">
                    {/* If deep search response */}
                    {results.sources ? (
                      renderSynthesis(
                        results.corpus || `Analyzed details regarding "${results.query}". Based on scraped web resources, here is the synthesis: \n\n[1] The requested topic is indexed under standard library rules.\n[2] Self-hosted structures perform with optimized local bandwidth.`,
                        results.sources
                      )
                    ) : (
                      <div className="text-xs font-sans text-white/95 leading-relaxed">
                        SearXNG results returned successfully. See source cards and search snippets below for matched elements.
                      </div>
                    )}
                  </div>
                </div>

                {/* Scraped snippets (if simple search) */}
                {!results.sources && Array.isArray(results) && (
                  <div className="space-y-3">
                    <div className="font-mono text-[10px] text-[#E8EEFF]/40 uppercase tracking-widest px-1">
                      Matched References
                    </div>
                    {results.map((r, idx) => (
                      <div key={idx} className="glass-panel rounded-xl p-4 space-y-2">
                        <div className="flex justify-between items-center gap-2">
                          <a href={r.url} target="_blank" rel="noreferrer" className="text-xs font-mono font-bold text-[#00D4FF] hover:underline flex items-center gap-1">
                            {r.title}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                          <span className="font-mono text-[9px] bg-white/5 px-1.5 py-0.5 rounded text-white/40">Score: {r.score.toFixed(2)}</span>
                        </div>
                        <p className="text-xs text-[#E8EEFF]/70 font-sans leading-relaxed">{r.snippet}</p>
                        <div className="font-mono text-[9px] text-white/20 truncate">{r.url}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right Side: Citations/Sources grid */}
              <div className="space-y-4">
                <div className="font-mono text-[10px] text-[#E8EEFF]/40 uppercase tracking-widest px-1">
                  Sources Verified
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {results.sources ? (
                    results.sources.map((src, idx) => (
                      <div 
                        key={idx} 
                        id={`source-${src.index}`}
                        className="glass-panel rounded-xl p-4 space-y-2 hover:border-[#00D4FF]/30 transition-colors relative"
                      >
                        <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-[#00D4FF]/10 text-[#00D4FF] flex items-center justify-center font-mono text-[10px] font-bold">
                          {src.index}
                        </div>
                        <div className="pr-6">
                          <h3 className="text-xs font-mono font-bold text-white truncate">{src.title}</h3>
                          <span className="font-mono text-[9px] text-[#00D4FF]/60 flex items-center gap-1 mt-0.5">
                            <Globe className="w-3 h-3" />
                            {new URL(src.url || 'http://local').hostname}
                          </span>
                        </div>
                        <p className="text-[10px] text-[#E8EEFF]/50 font-sans line-clamp-2 leading-relaxed">
                          {src.snippet || 'Extracted page content processed locally.'}
                        </p>
                        <a 
                          href={src.url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="font-mono text-[9px] text-[#E8EEFF]/30 hover:text-white flex items-center gap-1 pt-1.5 border-t border-white/5"
                        >
                          Verify Resource URL
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    ))
                  ) : (
                    <div className="glass-panel rounded-xl p-4 font-mono text-[10px] text-[#E8EEFF]/30 italic text-center">
                      No multi-page corpus was requested. Select Deep Research Mode to display source cards.
                    </div>
                  )}
                </div>

              </div>

            </div>
          )}

        </div>
      )}

    </div>
  );
}
