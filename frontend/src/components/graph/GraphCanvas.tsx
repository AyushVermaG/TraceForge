import React, { useEffect, useRef, useCallback } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
// @ts-ignore
import dagre from 'cytoscape-dagre';
import { GraphNode, GraphEdge, NodeKind, RelationshipKind } from '../../types/graph';

// Register dagre layout plugin once
cytoscape.use(dagre);

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  onExpandNode: (nodeId: string) => void;
  visibleNodeKinds: Set<NodeKind>;
  visibleRelKinds: Set<RelationshipKind>;
  layoutMode: 'dagre' | 'concentric';
  cyRefOut?: React.MutableRefObject<Core | null>;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  selectedNodeId,
  onSelectNode,
  onExpandNode,
  visibleNodeKinds,
  visibleRelKinds,
  layoutMode,
  cyRefOut,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Initialize cytoscape instance
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      boxSelectionEnabled: false,
      autounselectify: false,
      style: [
        // Default Node Style
        {
          selector: 'node',
          style: {
            'label': 'data(name)',
            'color': '#F1F5F9',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 5,
            'background-color': '#0B0F19',
            'border-width': 2,
            'border-color': '#334155',
            'width': 36,
            'height': 36,
            'transition-property': 'background-color, border-color, border-width',
            'transition-duration': 0.2,
          },
        },
        // Repository
        {
          selector: 'node[kind = "Repository"]',
          style: {
            'background-color': '#0B192C',
            'border-color': '#00F2FE',
            'border-width': 3,
            'width': 48,
            'height': 48,
            'font-weight': 'bold',
            'color': '#00F2FE',
          },
        },
        // File
        {
          selector: 'node[kind = "File"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#0F172A',
            'border-color': '#64748B',
            'width': 32,
            'height': 32,
            'color': '#CBD5E1',
          },
        },
        // Module
        {
          selector: 'node[kind = "Module"]',
          style: {
            'shape': 'round-rectangle',
            'background-color': '#0C223B',
            'border-color': '#38BDF8',
            'width': 34,
            'height': 34,
            'color': '#38BDF8',
          },
        },
        // Class
        {
          selector: 'node[kind = "Class"]',
          style: {
            'shape': 'diamond',
            'background-color': '#211036',
            'border-color': '#A855F7',
            'border-width': 2.5,
            'width': 38,
            'height': 38,
            'color': '#D8B4FE',
          },
        },
        // Function
        {
          selector: 'node[kind = "Function"]',
          style: {
            'shape': 'ellipse',
            'background-color': '#07241D',
            'border-color': '#10B981',
            'width': 32,
            'height': 32,
            'color': '#6EE7B7',
          },
        },
        // External Package
        {
          selector: 'node[kind = "ExternalPackage"]',
          style: {
            'shape': 'hexagon',
            'background-color': '#2B1E05',
            'border-color': '#F59E0B',
            'border-style': 'dashed',
            'width': 34,
            'height': 34,
            'color': '#FCD34D',
          },
        },
        // Selected Node Highlight
        {
          selector: 'node:selected',
          style: {
            'border-color': '#00F2FE',
            'border-width': 4,
            'background-color': '#082F49',
          },
        },
        // Default Edge Style
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#334155',
            'target-arrow-color': '#334155',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.8,
          },
        },
        // CONTAINS Edge
        {
          selector: 'edge[type = "CONTAINS"]',
          style: {
            'line-color': '#38BDF8',
            'target-arrow-color': '#38BDF8',
            'opacity': 0.7,
            'width': 1.5,
          },
        },
        // DEFINES Edge
        {
          selector: 'edge[type = "DEFINES"]',
          style: {
            'line-color': '#A855F7',
            'target-arrow-color': '#A855F7',
            'opacity': 0.8,
            'width': 2,
          },
        },
        // IMPORTS Edge
        {
          selector: 'edge[type = "IMPORTS"]',
          style: {
            'line-color': '#60A5FA',
            'target-arrow-color': '#60A5FA',
            'line-style': 'dashed',
            'opacity': 0.6,
            'width': 1.5,
          },
        },
        // CALLS Edge
        {
          selector: 'edge[type = "CALLS"]',
          style: {
            'line-color': '#10B981',
            'target-arrow-color': '#10B981',
            'line-style': 'dotted',
            'width': 2.5,
            'opacity': 0.9,
          },
        },
      ],
    });

    // Single click: select node
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      onSelectNode(node.id());
    });

    // Double click: expand neighborhood
    cy.on('dbltap', 'node', (evt: EventObject) => {
      const node = evt.target;
      onExpandNode(node.id());
    });

    cyRef.current = cy;
    if (cyRefOut) cyRefOut.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
      if (cyRefOut) cyRefOut.current = null;
    };
  }, []);

  // Update elements when nodes/edges/filters change
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    // Filter nodes by kind
    const filteredNodes = nodes.filter((n) => visibleNodeKinds.has(n.kind));
    const activeNodeIds = new Set(filteredNodes.map((n) => n.id));

    // Filter edges by relationship kind and active endpoints
    const filteredEdges = edges.filter(
      (e) => visibleRelKinds.has(e.type) && activeNodeIds.has(e.source) && activeNodeIds.has(e.target)
    );

    const elements = [
      ...filteredNodes.map((n) => ({
        group: 'nodes' as const,
        data: {
          id: n.id,
          name: n.name,
          kind: n.kind,
          properties: n.properties,
        },
      })),
      ...filteredEdges.map((e) => ({
        group: 'edges' as const,
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          properties: e.properties,
        },
      })),
    ];

    cy.elements().remove();
    cy.add(elements);

    // Compute deterministic layout
    runLayout();
  }, [nodes, edges, visibleNodeKinds, visibleRelKinds, layoutMode]);

  // Synchronize selection highlight
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().unselect();
    if (selectedNodeId) {
      const target = cy.$id(selectedNodeId);
      if (target.length > 0) {
        target.select();
      }
    }
  }, [selectedNodeId]);

  const runLayout = useCallback(() => {
    const cy = cyRef.current;
    if (!cy || cy.elements().length === 0) return;

    if (layoutMode === 'dagre') {
      cy.layout({
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 60,
        rankSep: 80,
        padding: 50,
        animate: true,
        animationDuration: 300,
      } as any).run();
    } else {
      cy.layout({
        name: 'concentric',
        concentric: (node: any) => {
          const kind = node.data('kind');
          if (kind === 'Repository') return 5;
          if (kind === 'Module' || kind === 'File') return 4;
          if (kind === 'Class') return 3;
          if (kind === 'Function') return 2;
          return 1;
        },
        levelWidth: () => 1,
        padding: 50,
        animate: true,
        animationDuration: 300,
      }).run();
    }
  }, [layoutMode]);

  return <div ref={containerRef} className="w-full h-full cyber-grid-bg cursor-grab active:cursor-grabbing" />;
};
