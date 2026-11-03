import {
  HealthResponse,
  RepositorySummary,
  UploadResponse,
  GraphResponse,
  SearchResponse,
  EvidenceDetail
} from '../types/graph';

const BASE_URL = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorMsg = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      } else if (errorJson.message) {
        errorMsg = errorJson.message;
      }
    } catch {
      // Ignore JSON parse failure
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${BASE_URL}/health`);
    return handleResponse<HealthResponse>(res);
  },

  async getRepositories(): Promise<RepositorySummary[]> {
    const res = await fetch(`${BASE_URL}/repositories`);
    const data = await handleResponse<{ repositories: RepositorySummary[] }>(res);
    return data.repositories;
  },

  async deleteRepository(repoId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/repositories/${encodeURIComponent(repoId)}`, {
      method: 'DELETE',
    });
    await handleResponse(res);
  },

  async uploadRepository(file: File, name: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);

    const res = await fetch(`${BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<UploadResponse>(res);
  },

  async getOverview(repoId: string, limit: number = 35): Promise<GraphResponse> {
    const res = await fetch(`${BASE_URL}/graph/overview?repo_id=${encodeURIComponent(repoId)}&limit=${limit}`);
    return handleResponse<GraphResponse>(res);
  },

  async expandNode(nodeId: string, limit: number = 30): Promise<GraphResponse> {
    const res = await fetch(`${BASE_URL}/graph/expand?node_id=${encodeURIComponent(nodeId)}&limit=${limit}`);
    return handleResponse<GraphResponse>(res);
  },

  async searchSymbols(query: string, repoId: string = '', limit: number = 20): Promise<SearchResponse> {
    const res = await fetch(`${BASE_URL}/graph/search?q=${encodeURIComponent(query)}&repo_id=${encodeURIComponent(repoId)}&limit=${limit}`);
    return handleResponse<SearchResponse>(res);
  },

  async getEvidence(nodeId: string): Promise<EvidenceDetail> {
    const res = await fetch(`${BASE_URL}/evidence/${encodeURIComponent(nodeId)}`);
    return handleResponse<EvidenceDetail>(res);
  },
};
