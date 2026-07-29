import api from "./client";
import type {
  Call,
  TranscriptEntry,
  PaginatedResponse,
  DashboardStats,
} from "../types";

// ── Calls ──

export interface FetchCallsParams {
  status?: string;
  page?: number;
  limit?: number;
}

export async function fetchCalls(
  params: FetchCallsParams = {}
): Promise<PaginatedResponse<Call>> {
  const { data } = await api.get("/calls", { params });
  return data;
}

export async function fetchCall(id: string): Promise<Call> {
  const { data } = await api.get(`/calls/${id}`);
  return data;
}

// ── Transcripts ──

export async function fetchCallTranscript(
  id: string
): Promise<TranscriptEntry[]> {
  const { data } = await api.get(`/calls/${id}/transcript`);
  return data;
}

// ── Dashboard ──

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get("/dashboard/stats");
  return data;
}
