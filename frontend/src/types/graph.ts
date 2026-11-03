export type NodeKind = 'Repository' | 'File' | 'Module' | 'Class' | 'Function' | 'ExternalPackage';
export type RelationshipKind = 'CONTAINS' | 'DEFINES' | 'IMPORTS' | 'CALLS';

export interface GraphNode {
  id: string;
  kind: NodeKind;
  name: string;
  properties: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: RelationshipKind;
  properties: Record<string, any>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes_in_scope: number;
  returned_nodes_count: number;
  truncated: boolean;
  message?: string;
}

export interface DependencyRef {
  node_id: string;
  name: string;
  kind: NodeKind;
  line_no?: number;
  confidence?: string;
  file_path?: string;
}

export interface EvidenceDetail {
  node_id: string;
  kind: NodeKind;
  name: string;
  qualified_name: string;
  file_path: string;
  start_line: number;
  end_line: number;
  docstring?: string;
  signature?: string;
  is_async?: boolean;
  is_method?: boolean;
  code_snippet: string;
  inbound_dependencies: DependencyRef[];
  outbound_dependencies: DependencyRef[];
}

export interface RepositorySummary {
  id: string;
  name: string;
  ingested_at: string;
  total_files: number;
  total_modules: number;
  total_classes: number;
  total_functions: number;
  total_calls: number;
}

export interface UploadResponse {
  repo_id: string;
  name: string;
  status: string;
  files_parsed: number;
  modules_found: number;
  classes_found: number;
  functions_found: number;
  calls_inferred: number;
  warnings: string[];
}

export interface SearchItem {
  id: string;
  kind: NodeKind;
  name: string;
  qualified_name: string;
  file_path?: string;
  line_no?: number;
}

export interface SearchResponse {
  query: string;
  results: SearchItem[];
  total: number;
}

export interface HealthResponse {
  status: string;
  environment: string;
  neo4j_connected: boolean;
  neo4j_uri_configured: boolean;
  neo4j_version?: string;
  error?: string;
}
