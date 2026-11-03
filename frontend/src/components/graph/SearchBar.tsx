import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Cpu, Share2, Box, FileCode, ArrowRight } from 'lucide-react';
import { api } from '../../api/client';
import { SearchItem, NodeKind } from '../../types/graph';

interface SearchBarProps {
  repoId: string;
  onSelectSymbol: (item: SearchItem) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ repoId, onSelectSymbol }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (!query.trim() || !repoId) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const resp = await api.searchSymbols(query.trim(), repoId, 15);
        setResults(resp.results);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, repoId]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getIcon = (kind: NodeKind) => {
    switch (kind) {
      case 'Class':
        return <Cpu className="w-3.5 h-3.5 text-cyber-violet" />;
      case 'Function':
        return <Share2 className="w-3.5 h-3.5 text-cyber-emerald" />;
      case 'Module':
        return <Box className="w-3.5 h-3.5 text-sky-400" />;
      default:
        return <FileCode className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div ref={searchRef} className="relative z-20 w-80">
      <div className="relative flex items-center">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder="Search symbols (Ctrl+K)..."
          className="w-full bg-midnight-900/90 border border-midnight-700 hover:border-midnight-600 focus:border-cyber-cyan rounded-xl pl-9 pr-8 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-500 backdrop-blur-md focus:outline-none transition-colors shadow-lg"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
            }}
            className="absolute right-2.5 text-slate-500 hover:text-slate-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Autocomplete Dropdown */}
      {isOpen && (query.trim().length > 0 || results.length > 0) && (
        <div className="absolute top-full mt-2 w-full bg-midnight-900/95 border border-midnight-700/80 rounded-xl shadow-2xl backdrop-blur-md overflow-hidden max-h-80 overflow-y-auto">
          {loading ? (
            <div className="p-3 text-center text-xs font-mono text-slate-500">Searching symbols...</div>
          ) : results.length === 0 ? (
            <div className="p-3 text-center text-xs font-mono text-slate-500">No matching symbols found</div>
          ) : (
            <div className="py-1">
              {results.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectSymbol(item);
                    setIsOpen(false);
                    setQuery('');
                  }}
                  className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-midnight-800/80 transition-colors border-b border-midnight-800 last:border-b-0"
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    {getIcon(item.kind)}
                    <div className="truncate">
                      <div className="flex items-center gap-1.5 font-mono text-xs text-slate-200 font-medium">
                        <span className="truncate">{item.name}</span>
                        <span className="text-[10px] text-slate-500">({item.kind})</span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono block truncate">
                        {item.file_path ? `${item.file_path}${item.line_no ? `:${item.line_no}` : ''}` : item.qualified_name}
                      </span>
                    </div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-600 flex-shrink-0 ml-2" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
