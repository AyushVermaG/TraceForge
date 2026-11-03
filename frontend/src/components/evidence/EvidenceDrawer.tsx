import React, { useState } from 'react';
import {
  X,
  FileCode,
  Share2,
  Cpu,
  Box,
  ExternalLink,
  ChevronRight,
  Code2,
  ArrowDownLeft,
  ArrowUpRight,
  Info
} from 'lucide-react';
import { EvidenceDetail, DependencyRef, NodeKind } from '../../types/graph';

interface EvidenceDrawerProps {
  evidence: EvidenceDetail | null;
  loading: boolean;
  onClose: () => void;
  onJumpToNode: (nodeId: string) => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  evidence,
  loading,
  onClose,
  onJumpToNode,
}) => {
  const [activeTab, setActiveTab] = useState<'code' | 'inbound' | 'outbound'>('code');

  if (!evidence && !loading) return null;

  const getKindColor = (kind: NodeKind) => {
    switch (kind) {
      case 'Repository':
        return 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10';
      case 'Module':
      case 'File':
        return 'border-sky-400 text-sky-400 bg-sky-400/10';
      case 'Class':
        return 'border-cyber-violet text-cyber-violet bg-cyber-violet/10';
      case 'Function':
        return 'border-cyber-emerald text-cyber-emerald bg-cyber-emerald/10';
      default:
        return 'border-cyber-amber text-cyber-amber bg-cyber-amber/10';
    }
  };

  return (
    <div className="fixed top-16 right-0 bottom-0 w-[480px] bg-midnight-950/95 border-l border-midnight-700/80 shadow-2xl backdrop-blur-lg flex flex-col z-30 transition-transform duration-300">
      {/* Drawer Header */}
      <div className="p-4 border-b border-midnight-800 flex items-start justify-between">
        <div className="space-y-1 overflow-hidden pr-3">
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-semibold uppercase ${
                evidence ? getKindColor(evidence.kind) : 'border-slate-700 text-slate-400'
              }`}
            >
              {evidence?.kind || 'Loading'}
            </span>
            {evidence?.is_async && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-midnight-800 text-cyan-400 border border-midnight-700">
                async
              </span>
            )}
            {evidence?.is_method && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-midnight-800 text-purple-400 border border-midnight-700">
                method
              </span>
            )}
          </div>
          <h2 className="text-base font-bold text-white font-mono truncate" title={evidence?.name}>
            {evidence?.name || 'Loading entity...'}
          </h2>
          <p className="text-[11px] text-slate-400 font-mono truncate" title={evidence?.file_path}>
            {evidence?.file_path ? `${evidence.file_path} (L${evidence.start_line}-L${evidence.end_line})` : ''}
          </p>
        </div>

        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-midnight-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-3">
          <div className="w-8 h-8 border-2 border-cyber-cyan border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-mono text-slate-400">Loading source evidence...</p>
        </div>
      ) : evidence ? (
        <>
          {/* Navigation Tabs */}
          <div className="flex border-b border-midnight-800 bg-midnight-900/60 px-4">
            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-1.5 py-2.5 px-3 text-xs font-mono border-b-2 transition-colors ${
                activeTab === 'code'
                  ? 'border-cyber-cyan text-cyber-cyan font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>Source Slice</span>
            </button>
            <button
              onClick={() => setActiveTab('inbound')}
              className={`flex items-center gap-1.5 py-2.5 px-3 text-xs font-mono border-b-2 transition-colors ${
                activeTab === 'inbound'
                  ? 'border-cyber-emerald text-cyber-emerald font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <ArrowDownLeft className="w-3.5 h-3.5" />
              <span>Callers ({evidence.inbound_dependencies.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('outbound')}
              className={`flex items-center gap-1.5 py-2.5 px-3 text-xs font-mono border-b-2 transition-colors ${
                activeTab === 'outbound'
                  ? 'border-cyber-violet text-cyber-violet font-semibold'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>Callees ({evidence.outbound_dependencies.length})</span>
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Signature & Docstring Bar */}
            {evidence.signature && (
              <div className="bg-midnight-900 border border-midnight-800 rounded-lg p-2.5 font-mono text-xs text-sky-300">
                <span className="text-slate-500 text-[10px] block mb-0.5">SIGNATURE</span>
                <span className="text-slate-300">{evidence.name}</span>
                <span className="text-slate-400">{evidence.signature}</span>
              </div>
            )}

            {evidence.docstring && (
              <div className="bg-midnight-900/60 border border-midnight-800/60 rounded-lg p-2.5 font-mono text-xs text-slate-300">
                <span className="text-slate-500 text-[10px] block mb-0.5">DOCSTRING</span>
                <p className="italic text-slate-300 whitespace-pre-wrap">{evidence.docstring}</p>
              </div>
            )}

            {activeTab === 'code' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Exact Definition Extract</span>
                  <span className="text-slate-500">Lines {evidence.start_line} - {evidence.end_line}</span>
                </div>
                <div className="bg-midnight-950 border border-midnight-800 rounded-xl overflow-x-auto shadow-inner">
                  <pre className="p-3 font-code text-xs text-slate-200 leading-relaxed overflow-x-auto">
                    <code>
                      {evidence.code_snippet.split('\n').map((line, idx) => {
                        const lineNum = evidence.start_line + idx;
                        return (
                          <div key={idx} className="table-row hover:bg-midnight-900/50">
                            <span className="table-cell select-none pr-4 text-right text-slate-600 text-[11px] font-mono w-10">
                              {lineNum}
                            </span>
                            <span className="table-cell whitespace-pre">{line}</span>
                          </div>
                        );
                      })}
                    </code>
                  </pre>
                </div>
              </div>
            )}

            {activeTab === 'inbound' && (
              <div className="space-y-2">
                {evidence.inbound_dependencies.length === 0 ? (
                  <div className="p-6 text-center text-xs font-mono text-slate-500 border border-dashed border-midnight-800 rounded-xl">
                    No inbound callers recorded for this symbol.
                  </div>
                ) : (
                  evidence.inbound_dependencies.map((dep, idx) => (
                    <div
                      key={idx}
                      className="bg-midnight-900/80 border border-midnight-800 hover:border-midnight-700 rounded-xl p-3 flex items-center justify-between group transition-colors"
                    >
                      <div className="overflow-hidden pr-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-semibold text-slate-200 truncate">
                            {dep.name}
                          </span>
                          {dep.confidence && (
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${
                                dep.confidence === 'exact'
                                  ? 'bg-cyber-emerald/10 border-cyber-emerald/30 text-cyber-emerald'
                                  : 'bg-cyber-amber/10 border-cyber-amber/30 text-cyber-amber'
                              }`}
                            >
                              {dep.confidence}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono block truncate">
                          {dep.file_path ? `${dep.file_path}${dep.line_no ? `:${dep.line_no}` : ''}` : dep.node_id}
                        </span>
                      </div>
                      <button
                        onClick={() => onJumpToNode(dep.node_id)}
                        className="flex items-center gap-1 text-[11px] font-mono text-cyber-cyan hover:text-white bg-cyber-cyan/10 hover:bg-cyber-cyan/20 border border-cyber-cyan/30 px-2 py-1 rounded-lg transition-colors flex-shrink-0"
                      >
                        <span>Inspect</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'outbound' && (
              <div className="space-y-2">
                {evidence.outbound_dependencies.length === 0 ? (
                  <div className="p-6 text-center text-xs font-mono text-slate-500 border border-dashed border-midnight-800 rounded-xl">
                    No outbound dependencies recorded for this symbol.
                  </div>
                ) : (
                  evidence.outbound_dependencies.map((dep, idx) => (
                    <div
                      key={idx}
                      className="bg-midnight-900/80 border border-midnight-800 hover:border-midnight-700 rounded-xl p-3 flex items-center justify-between group transition-colors"
                    >
                      <div className="overflow-hidden pr-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-semibold text-slate-200 truncate">
                            {dep.name}
                          </span>
                          {dep.confidence && (
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${
                                dep.confidence === 'exact'
                                  ? 'bg-cyber-emerald/10 border-cyber-emerald/30 text-cyber-emerald'
                                  : 'bg-cyber-amber/10 border-cyber-amber/30 text-cyber-amber'
                              }`}
                            >
                              {dep.confidence}
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono block truncate">
                          {dep.file_path ? `${dep.file_path}${dep.line_no ? `:${dep.line_no}` : ''}` : dep.node_id}
                        </span>
                      </div>
                      <button
                        onClick={() => onJumpToNode(dep.node_id)}
                        className="flex items-center gap-1 text-[11px] font-mono text-cyber-violet hover:text-white bg-cyber-violet/10 hover:bg-cyber-violet/20 border border-cyber-violet/30 px-2 py-1 rounded-lg transition-colors flex-shrink-0"
                      >
                        <span>Inspect</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
};
