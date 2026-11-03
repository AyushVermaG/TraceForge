import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Core } from 'cytoscape';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { GraphCanvas } from './components/graph/GraphCanvas';
import { GraphControls } from './components/graph/GraphControls';
import { SearchBar } from './components/graph/SearchBar';
import { EvidenceDrawer } from './components/evidence/EvidenceDrawer';
import { UploadModal } from './components/upload/UploadModal';
import { api } from './api/client';
import {
  HealthResponse,
  RepositorySummary,
  GraphNode,
  GraphEdge,
  NodeKind,
  RelationshipKind,
  EvidenceDetail,
  SearchItem,
  UploadResponse
} from './types/graph';
import { FolderGit2, UploadCloud, AlertCircle, Sparkles } from 'lucide-react';

export const App: React.FC = () => {
  // Application Data States
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [activeRepoId, setActiveRepoId] = useState<string | null>(null);

  // Graph Data States
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [totalScopeCount, setTotalScopeCount] = useState<number>(0);
  const [truncationMsg, setTruncationMsg] = useState<string | null>(null);
  const [graphLoading, setGraphLoading] = useState<boolean>(false);

  // Filter States
  const [visibleNodeKinds, setVisibleNodeKinds] = useState<Set<NodeKind>>(
    new Set<NodeKind>(['Repository', 'Module', 'File', 'Class', 'Function', 'ExternalPackage'])
  );
  const [visibleRelKinds, setVisibleRelKinds] = useState<Set<RelationshipKind>>(
    new Set<RelationshipKind>(['CONTAINS', 'DEFINES', 'IMPORTS', 'CALLS'])
  );
  const [layoutMode, setLayoutMode] = useState<'dagre' | 'concentric'>('dagre');

  // Evidence & Inspector States
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<EvidenceDetail | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState<boolean>(false);

  // Modal State
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);

  // Cytoscape Reference for controls
  const cyRef = useRef<Core | null>(null);

  // 1. Initial Health Check & Repositories Fetch
  const refreshMetadata = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch (err) {
      console.error('Health check failed:', err);
    }

    try {
      const repos = await api.getRepositories();
      setRepositories(repos);
      if (repos.length > 0 && !activeRepoId) {
        setActiveRepoId(repos[0].id);
      }
    } catch (err) {
      console.error('Repositories list failed:', err);
    }
  }, [activeRepoId]);

  useEffect(() => {
    refreshMetadata();
    // Poll health status every 30 seconds
    const interval = setInterval(async () => {
      try {
        const h = await api.getHealth();
        setHealth(h);
      } catch {}
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshMetadata]);

  // 2. Fetch Graph Overview when activeRepoId changes
  const loadRepositoryOverview = useCallback(async (repoId: string) => {
    if (!repoId) return;
    setGraphLoading(true);
    setSelectedNodeId(null);
    setEvidence(null);

    try {
      const overview = await api.getOverview(repoId, 35);
      setNodes(overview.nodes);
      setEdges(overview.edges);
      setTotalScopeCount(overview.total_nodes_in_scope);
      setTruncationMsg(overview.message || null);
    } catch (err: any) {
      console.error('Failed to load overview:', err);
    } finally {
      setGraphLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeRepoId) {
      loadRepositoryOverview(activeRepoId);
    } else {
      setNodes([]);
      setEdges([]);
      setTotalScopeCount(0);
      setTruncationMsg(null);
    }
  }, [activeRepoId, loadRepositoryOverview]);

  // 3. Node Selection -> Fetch Evidence
  const handleSelectNode = useCallback(async (nodeId: string) => {
    setSelectedNodeId(nodeId);
    setEvidenceLoading(true);
    try {
      const ev = await api.getEvidence(nodeId);
      setEvidence(ev);
    } catch (err: any) {
      console.error('Failed to load evidence for node:', nodeId, err);
    } finally {
      setEvidenceLoading(false);
    }
  }, []);

  // 4. Double-Click -> Progressive Neighborhood Expansion
  const handleExpandNode = useCallback(async (nodeId: string) => {
    try {
      const expansion = await api.expandNode(nodeId, 30);
      
      // Merge new nodes
      setNodes((prevNodes) => {
        const existingIds = new Set(prevNodes.map((n) => n.id));
        const newNodes = expansion.nodes.filter((n) => !existingIds.has(n.id));
        return [...prevNodes, ...newNodes];
      });

      // Merge new edges
      setEdges((prevEdges) => {
        const existingIds = new Set(prevEdges.map((e) => e.id));
        const newEdges = expansion.edges.filter((e) => !existingIds.has(e.id));
        return [...prevEdges, ...newEdges];
      });

      // Also select the node for evidence inspection
      handleSelectNode(nodeId);
    } catch (err) {
      console.error('Failed to expand neighborhood:', err);
    }
  }, [handleSelectNode]);

  // 5. Jump to symbol from Search or Evidence Drawer
  const handleJumpToSymbol = useCallback(async (nodeId: string) => {
    handleSelectNode(nodeId);
    handleExpandNode(nodeId);

    // Zoom/pan cy to target node
    if (cyRef.current) {
      const target = cyRef.current.$id(nodeId);
      if (target.length > 0) {
        cyRef.current.animate({
          center: { eles: target },
          zoom: 1.5,
          duration: 400,
        });
      }
    }
  }, [handleSelectNode, handleExpandNode]);

  // Filter Toggles
  const toggleNodeKind = (kind: NodeKind) => {
    setVisibleNodeKinds((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  };

  const toggleRelKind = (kind: RelationshipKind) => {
    setVisibleRelKinds((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  };

  // Upload Complete Callback
  const handleUploadSuccess = (response: UploadResponse) => {
    refreshMetadata();
    setActiveRepoId(response.repo_id);
  };

  // Repository Deletion
  const handleDeleteRepository = async (repoId: string) => {
    try {
      await api.deleteRepository(repoId);
      const updated = repositories.filter((r) => r.id !== repoId);
      setRepositories(updated);
      if (activeRepoId === repoId) {
        setActiveRepoId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (err) {
      console.error('Failed to delete repository:', err);
    }
  };

  // Cytoscape Viewport Helpers
  const handleZoomIn = () => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() * 1.25);
  };
  const handleZoomOut = () => {
    if (cyRef.current) cyRef.current.zoom(cyRef.current.zoom() * 0.8);
  };
  const handleFit = () => {
    if (cyRef.current) cyRef.current.fit(undefined, 50);
  };
  const handleResetLayout = () => {
    if (activeRepoId) loadRepositoryOverview(activeRepoId);
  };

  const activeRepo = repositories.find((r) => r.id === activeRepoId) || null;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-midnight-950 text-slate-100">
      {/* Top Navigation Bar */}
      <Navbar
        health={health}
        repositories={repositories}
        activeRepoId={activeRepoId}
        onSelectRepo={(id) => setActiveRepoId(id)}
        onOpenUpload={() => setUploadModalOpen(true)}
      />

      {/* Main Work Area */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Telemetry & Filter Sidebar */}
        <Sidebar
          activeRepo={activeRepo}
          renderedNodeCount={nodes.length}
          totalScopeCount={totalScopeCount}
          visibleNodeKinds={visibleNodeKinds}
          onToggleNodeKind={toggleNodeKind}
          visibleRelKinds={visibleRelKinds}
          onToggleRelKind={toggleRelKind}
          onResetToOverview={() => activeRepoId && loadRepositoryOverview(activeRepoId)}
          onDeleteRepo={handleDeleteRepository}
        />

        {/* Center: Graph Canvas Viewport */}
        <main className="flex-1 relative overflow-hidden flex flex-col">
          {/* Top Floating Search & Quick Filters Bar */}
          {activeRepoId && (
            <div className="absolute top-5 left-5 z-20 flex items-center gap-3">
              <SearchBar
                repoId={activeRepoId}
                onSelectSymbol={(item: SearchItem) => handleJumpToSymbol(item.id)}
              />

              {truncationMsg && (
                <div className="bg-midnight-900/90 border border-midnight-700/80 backdrop-blur-md px-3.5 py-2 rounded-xl text-xs font-mono text-slate-300 flex items-center gap-2 shadow-lg">
                  <AlertCircle className="w-3.5 h-3.5 text-cyber-cyan flex-shrink-0" />
                  <span>{truncationMsg}</span>
                </div>
              )}
            </div>
          )}

          {/* Canvas or Empty State */}
          {activeRepoId ? (
            <div className="w-full h-full relative">
              {graphLoading && (
                <div className="absolute inset-0 z-10 bg-midnight-950/50 backdrop-blur-xs flex items-center justify-center">
                  <div className="flex items-center gap-2.5 bg-midnight-900/90 border border-midnight-700 px-4 py-2.5 rounded-xl font-mono text-xs text-cyber-cyan">
                    <div className="w-4 h-4 border-2 border-cyber-cyan border-t-transparent rounded-full animate-spin" />
                    <span>Rendering Bounded Architecture Graph...</span>
                  </div>
                </div>
              )}

              <GraphCanvas
                nodes={nodes}
                edges={edges}
                selectedNodeId={selectedNodeId}
                onSelectNode={handleSelectNode}
                onExpandNode={handleExpandNode}
                visibleNodeKinds={visibleNodeKinds}
                visibleRelKinds={visibleRelKinds}
                layoutMode={layoutMode}
                cyRefOut={cyRef}
              />

              {/* Viewport Control Tools */}
              <GraphControls
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onFit={handleFit}
                onResetLayout={handleResetLayout}
                layoutMode={layoutMode}
                onToggleLayout={(mode) => setLayoutMode(mode)}
              />
            </div>
          ) : (
            /* Welcome / Zero State */
            <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center space-y-5 cyber-grid-bg">
              <div className="w-16 h-16 rounded-2xl bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center shadow-glow-cyan">
                <FolderGit2 className="w-8 h-8 text-cyber-cyan" />
              </div>
              <div className="max-w-md space-y-2">
                <h2 className="text-xl font-bold text-white font-mono">No Repositories Ingested Yet</h2>
                <p className="text-xs text-slate-400 font-mono leading-relaxed">
                  Upload a Python repository ZIP to extract modules, classes, functions, and statically inferable calls into Neo4j.
                </p>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => setUploadModalOpen(true)}
                  className="flex items-center gap-2 bg-cyber-cyan hover:bg-cyber-cyan/90 text-midnight-950 text-xs font-bold font-mono px-5 py-2.5 rounded-xl transition-all shadow-glow-cyan active:scale-95"
                >
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload Python ZIP</span>
                </button>
              </div>

              <div className="text-[11px] font-mono text-slate-500 pt-6 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-cyber-violet" />
                <span>Tip: A sample Python repository is available in <code>sample_repo/sample_repo.zip</code></span>
              </div>
            </div>
          )}

          {/* Right Slide-Out Evidence Drawer */}
          <EvidenceDrawer
            evidence={evidence}
            loading={evidenceLoading}
            onClose={() => {
              setSelectedNodeId(null);
              setEvidence(null);
            }}
            onJumpToNode={handleJumpToSymbol}
          />
        </main>
      </div>

      {/* Upload ZIP Modal */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
};
