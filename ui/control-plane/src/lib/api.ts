import type {
  AgentApi,
  MutationHistoryItem,
  ReflectionItem,
  StatisticsResponse,
} from "../types/controlPlane";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 1800);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }

    return (await response.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getStatistics(): Promise<StatisticsResponse> {
  return fetchJson<StatisticsResponse>("/api/v1/statistics");
}

export async function getAgents(): Promise<AgentApi[]> {
  return fetchJson<AgentApi[]>("/api/v1/agents");
}

export async function getMutationHistory(limit = 40): Promise<MutationHistoryItem[]> {
  const res = await fetchJson<{ mutation_history: MutationHistoryItem[] }>(
    `/api/v1/mutation/history?limit=${limit}`,
  );
  return res.mutation_history;
}

export async function getReflections(limit = 30): Promise<ReflectionItem[]> {
  const res = await fetchJson<{ reflections: ReflectionItem[] }>(`/api/v1/reflections?limit=${limit}`);
  return res.reflections;
}

export { API_BASE_URL };
