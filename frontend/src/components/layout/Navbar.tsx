import React from 'react';
import { Database, Shield, UploadCloud, ChevronDown, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import { RepositorySummary, HealthResponse } from '../../types/graph';

interface NavbarProps {
  health: HealthResponse | null;
  repositories: RepositorySummary[];
  activeRepoId: string | null;
  onSelectRepo: (id: string) => void;
  onOpenUpload: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  repositories,
  activeRepoId,
  onSelectRepo,
  onOpenUpload,
}) => {
  const activeRepo = repositories.find((r) => r.id === activeRepoId);

  return (
    <header className="h-16 border-b border-midnight-700 bg-midnight-900/90 backdrop-blur-md px-5 flex items-center justify-between select-none z-30">
      {/* Brand Identity */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center shadow-glow-cyan">
          <Shield className="w-5 h-5 text-cyber-cyan" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-wider text-white">
              TRACE<span className="text-cyber-cyan glow-cyan-text">FORGE</span>
            </span>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-midnight-800 border border-midnight-600 text-slate-400">
              v1.0.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 -mt-0.5 font-mono">Evidence-First Codebase Intelligence</p>
        </div>
      </div>

      {/* Middle: Active Repository Selector */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <select
            value={activeRepoId || ''}
            onChange={(e) => onSelectRepo(e.target.value)}
            disabled={repositories.length === 0}
            className="appearance-none bg-midnight-950 border border-midnight-700 hover:border-midnight-600 rounded-lg pl-3.5 pr-9 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyber-cyan cursor-pointer transition-colors"
          >
            {repositories.length === 0 ? (
              <option value="">No Repositories Ingested</option>
            ) : (
              repositories.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name} ({repo.total_files} files, {repo.total_calls} calls)
                </option>
              ))
            )}
          </select>
          <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Right: DB Health Badge & Upload Button */}
      <div className="flex items-center gap-3">
        {/* Neo4j Status Badge */}
        <div
          title={health?.error || (health?.neo4j_connected ? `Connected to ${health.neo4j_version}` : 'Neo4j Unreachable')}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono border transition-colors ${
            health?.neo4j_connected
              ? 'bg-cyber-emerald/10 border-cyber-emerald/30 text-cyber-emerald'
              : health?.neo4j_uri_configured
              ? 'bg-cyber-amber/10 border-cyber-amber/30 text-cyber-amber'
              : 'bg-cyber-rose/10 border-cyber-rose/30 text-cyber-rose'
          }`}
        >
          {health?.neo4j_connected ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-cyber-emerald" />
          ) : health?.neo4j_uri_configured ? (
            <AlertTriangle className="w-3.5 h-3.5 text-cyber-amber" />
          ) : (
            <XCircle className="w-3.5 h-3.5 text-cyber-rose" />
          )}
          <span>
            {health?.neo4j_connected
              ? `NEO4J: ONLINE`
              : health?.neo4j_uri_configured
              ? `NEO4J: OFFLINE`
              : `NEO4J: UNCONFIGURED`}
          </span>
        </div>

        {/* Upload Repository Button */}
        <button
          onClick={onOpenUpload}
          className="flex items-center gap-2 bg-cyber-cyan/15 hover:bg-cyber-cyan/25 border border-cyber-cyan/40 text-cyber-cyan text-xs font-semibold px-3.5 py-1.5 rounded-lg transition-all shadow-glow-cyan active:scale-95"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Ingest Repo ZIP</span>
        </button>
      </div>
    </header>
  );
};
