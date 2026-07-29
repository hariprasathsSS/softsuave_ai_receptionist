// ── Call & Transcript Types ──

export type CallStatus = "ringing" | "active" | "ended" | "missed" | "voicemail";
export type TranscriptSpeaker = "human" | "ai";

export interface Call {
  id: string;
  caller_number: string;
  caller_name: string | null;
  status: CallStatus;
  direction: "inbound" | "outbound";
  start_time: string; // ISO 8601
  end_time: string | null;
  duration_seconds: number | null;
  profile_id: string | null;
  profile_name: string | null;
  recording_url: string | null;
  transcript_count: number;
}

export interface TranscriptEntry {
  id: string;
  call_id: string;
  speaker: TranscriptSpeaker;
  text: string;
  timestamp: string; // ISO 8601 with ms
  sequence: number;
}

// ── WebSocket Message Types (Live Monitoring) ──

export type WSMessage =
  | { type: "call_started"; call: Call }
  | {
      type: "transcript";
      call_id: string;
      speaker: TranscriptSpeaker;
      text: string;
      timestamp: string;
      sequence: number;
    }
  | { type: "call_updated"; call: Partial<Call> & { id: string } }
  | {
      type: "call_ended";
      call_id: string;
      end_time: string;
      duration_seconds: number;
    };

// ── API Response Wrappers ──

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface DashboardStats {
  active_profiles: number;
  calls_today: number;
  bookings_today: number;
  active_calls: number;
}
