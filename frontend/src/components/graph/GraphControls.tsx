import React from 'react';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, GitFork, Compass } from 'lucide-react';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  onResetLayout: () => void;
  layoutMode: 'dagre' | 'concentric';
  onToggleLayout: (mode: 'dagre' | 'concentric') => void;
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onFit,
  onResetLayout,
  layoutMode,
  onToggleLayout,
}) => {
  return (
    <div className="absolute bottom-5 right-5 z-20 flex items-center gap-1.5 bg-midnight-900/90 border border-midnight-700/80 backdrop-blur-md p-1.5 rounded-xl shadow-xl">
      {/* Zoom In */}
      <button
        onClick={onZoomIn}
        title="Zoom In"
        className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-midnight-800 transition-colors"
      >
        <ZoomIn className="w-4 h-4" />
      </button>

      {/* Zoom Out */}
      <button
        onClick={onZoomOut}
        title="Zoom Out"
        className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-midnight-800 transition-colors"
      >
        <ZoomOut className="w-4 h-4" />
      </button>

      <div className="w-[1px] h-4 bg-midnight-700 mx-0.5" />

      {/* Fit to View */}
      <button
        onClick={onFit}
        title="Fit Graph to Viewport"
        className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-midnight-800 transition-colors"
      >
        <Maximize2 className="w-4 h-4" />
      </button>

      {/* Re-run Layout */}
      <button
        onClick={onResetLayout}
        title="Recompute Layout"
        className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-midnight-800 transition-colors"
      >
        <RotateCcw className="w-4 h-4" />
      </button>

      <div className="w-[1px] h-4 bg-midnight-700 mx-0.5" />

      {/* Toggle Hierarchical / Radial */}
      <button
        onClick={() => onToggleLayout(layoutMode === 'dagre' ? 'concentric' : 'dagre')}
        title={`Current Layout: ${layoutMode === 'dagre' ? 'Hierarchical (Dagre)' : 'Radial (Concentric)'}. Click to switch.`}
        className={`px-2.5 h-8 rounded-lg flex items-center gap-1.5 text-xs font-mono font-medium border transition-colors ${
          layoutMode === 'dagre'
            ? 'bg-cyber-cyan/15 border-cyber-cyan/40 text-cyber-cyan'
            : 'bg-cyber-violet/15 border-cyber-violet/40 text-cyber-violet'
        }`}
      >
        {layoutMode === 'dagre' ? <GitFork className="w-3.5 h-3.5" /> : <Compass className="w-3.5 h-3.5" />}
        <span>{layoutMode === 'dagre' ? 'Dagre' : 'Concentric'}</span>
      </button>
    </div>
  );
};
