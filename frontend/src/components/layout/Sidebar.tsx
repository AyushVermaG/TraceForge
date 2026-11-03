import React from 'react';
import {
  Layers,
  FileCode,
  Box,
  Cpu,
  Share2,
  Filter,
  RefreshCw,
  FolderTree,
  ExternalLink,
  Sliders,
  Trash2
} from 'lucide-react';
import { RepositorySummary, NodeKind, RelationshipKind } from '../../types/graph';

interface SidebarProps {
  activeRepo: RepositorySummary | null;
  renderedNodeCount: number;
  totalScopeCount: number;
  visibleNodeKinds: Set<NodeKind>;
  onToggleNodeKind: (kind: NodeKind) => void;
  visibleRelKinds: Set<RelationshipKind>;
  onToggleRelKind: (kind: RelationshipKind) => void;
  onResetToOverview: () => void;
  onDeleteRepo: (repoId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeRepo,
  renderedNodeCount,
  totalScopeCount,
  visibleNodeKinds,
  onToggleNodeKind,
  visibleRelKinds,
  onToggleRelKind,
  onResetToOverview,
  onDeleteRepo,
}) => {
  return (
    <aside className="w-72 border-r border-midnight-700 bg-midnight-900/60 backdrop-blur-sm flex flex-col h-[calc(100vh-4rem)] select-none">
      {/* Scrollable Configuration Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Repository Telemetry Card */}
        {activeRepo ? (
          <div className="bg-midnight-950/80 border border-midnight-700/80 rounded-xl p-3.5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wider font-mono text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyber-cyan" />
                Repository Telemetry
              </span>
              <button
                onClick={() => {
                  if (confirm(`Are you sure you want to delete repository "${activeRepo.name}"?`)) {
                    onDeleteRepo(activeRepo.id);
                  }
                }}
                title="Delete Repository"
                className="text-slate-500 hover:text-cyber-rose p-1 rounded transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-midnight-900/90 border border-midnight-700/50 rounded-lg p-2">
                <span className="text-slate-400 text-[10px] block">Files</span>
                <span className="text-white font-semibold text-sm">{activeRepo.total_files}</span>
              </div>
              <div className="bg-midnight-900/90 border border-midnight-700/50 rounded-lg p-2">
                <span className="text-slate-400 text-[10px] block">Modules</span>
                <span className="text-sky-400 font-semibold text-sm">{activeRepo.total_modules}</span>
              </div>
              <div className="bg-midnight-900/90 border border-midnight-700/50 rounded-lg p-2">
                <span className="text-slate-400 text-[10px] block">Classes</span>
                <span className="text-cyber-violet font-semibold text-sm">{activeRepo.total_classes}</span>
              </div>
              <div className="bg-midnight-900/90 border border-midnight-700/50 rounded-lg p-2">
                <span className="text-slate-400 text-[10px] block">Functions</span>
                <span className="text-cyber-emerald font-semibold text-sm">{activeRepo.total_functions}</span>
              </div>
            </div>

            <div className="pt-1 flex items-center justify-between text-[11px] font-mono text-slate-400 border-t border-midnight-800">
              <span>Static Calls Inferred:</span>
              <span className="text-cyber-cyan font-bold">{activeRepo.total_calls}</span>
            </div>
          </div>
        ) : (
          <div className="bg-midnight-950/60 border border-dashed border-midnight-700 rounded-xl p-4 text-center">
            <FolderTree className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400">No active repository selected</p>
          </div>
        )}

        {/* Node Filters */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-300">
            <span className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-cyber-cyan" />
              Node Kinds
            </span>
            <span className="text-[10px] text-slate-500">{visibleNodeKinds.size}/6</span>
          </div>

          <div className="space-y-1.5 font-mono text-xs">
            {[
              { kind: 'Repository' as NodeKind, color: '#00F2FE', label: 'Repository', icon: Layers },
              { kind: 'Module' as NodeKind, color: '#38BDF8', label: 'Module', icon: Box },
              { kind: 'File' as NodeKind, color: '#94A3B8', label: 'File', icon: FileCode },
              { kind: 'Class' as NodeKind, color: '#A855F7', label: 'Class', icon: Cpu },
              { kind: 'Function' as NodeKind, color: '#10B981', label: 'Function', icon: Share2 },
              { kind: 'ExternalPackage' as NodeKind, color: '#F59E0B', label: 'Package', icon: ExternalLink },
            ].map(({ kind, color, label, icon: Icon }) => {
              const active = visibleNodeKinds.has(kind);
              return (
                <button
                  key={kind}
                  onClick={() => onToggleNodeKind(kind)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-left transition-all ${
                    active
                      ? 'bg-midnight-950 border-midnight-700 text-slate-200'
                      : 'bg-transparent border-transparent text-slate-500 hover:text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                    <Icon className="w-3.5 h-3.5 opacity-70" />
                    <span>{label}</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={active}
                    readOnly
                    className="accent-cyber-cyan rounded cursor-pointer"
                  />
                </button>
              );
            })}
          </div>
        </div>

        {/* Relationship Filters */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-300">
            <span className="flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyber-violet" />
              Relationships
            </span>
            <span className="text-[10px] text-slate-500">{visibleRelKinds.size}/4</span>
          </div>

          <div className="space-y-1.5 font-mono text-xs">
            {[
              { kind: 'CONTAINS' as RelationshipKind, style: 'Solid slate-cyan', desc: 'Hierarchy' },
              { kind: 'DEFINES' as RelationshipKind, style: 'Solid violet', desc: 'Definition' },
              { kind: 'IMPORTS' as RelationshipKind, style: 'Dashed sky-blue', desc: 'Import' },
              { kind: 'CALLS' as RelationshipKind, style: 'Dotted emerald', desc: 'Invocation' },
            ].map(({ kind, style, desc }) => {
              const active = visibleRelKinds.has(kind);
              return (
                <button
                  key={kind}
                  onClick={() => onToggleRelKind(kind)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-left transition-all ${
                    active
                      ? 'bg-midnight-950 border-midnight-700 text-slate-200'
                      : 'bg-transparent border-transparent text-slate-500 hover:text-slate-400'
                  }`}
                >
                  <div>
                    <span className="font-semibold block">{kind}</span>
                    <span className="text-[10px] text-slate-500 block">{desc}</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={active}
                    readOnly
                    className="accent-cyber-violet rounded cursor-pointer"
                  />
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer Bounded Limit Indicator & Reset */}
      <div className="p-3 border-t border-midnight-700 bg-midnight-950/70 space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Active Entities:</span>
          <span className="text-white font-bold">{renderedNodeCount}</span>
        </div>

        <button
          onClick={onResetToOverview}
          className="w-full flex items-center justify-center gap-2 bg-midnight-800 hover:bg-midnight-700 border border-midnight-600 text-slate-200 text-xs font-mono py-1.5 rounded-lg transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 text-cyber-cyan" />
          <span>Reset to Overview</span>
        </button>
      </div>
    </aside>
  );
};
