import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { Call, TranscriptEntry, WSMessage } from "../../types";
import { useWebSocket } from "../../hooks/useWebSocket";
import CallStatusBadge from "../../components/CallStatusBadge";
import TranscriptView from "../../components/TranscriptView";
import { Button, Badge, Spinner } from "../../components/ui/Button";

// WebSocket URL: uses Vite proxy in dev, direct backend connection in production
function getWsUrl(): string {
  const isDev = import.meta.env.DEV;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = isDev ? window.location.host : `${window.location.hostname}:8000`;
  // Try to pass stored auth token as query param for backend auth
  const token = localStorage.getItem("access_token");
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${protocol}//${host}/voice/ws${tokenParam}`;
}

export default function LiveMonitor() {
  const navigate = useNavigate();

  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [callEnded, setCallEnded] = useState(false);
  const [finalCall, setFinalCall] = useState<Call | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Handle incoming WebSocket messages ──
  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case "call_started":
        setActiveCall(msg.call);
        setTranscript([]);
        setCallEnded(false);
        setFinalCall(null);
        setElapsed(0);
        break;

      case "transcript":
        setTranscript((prev) => [
          ...prev,
          {
            id: `${msg.call_id}-${msg.sequence}`,
            call_id: msg.call_id,
            speaker: msg.speaker,
            text: msg.text,
            timestamp: msg.timestamp,
            sequence: msg.sequence,
          },
        ]);
        break;

      case "call_updated":
        setActiveCall((prev) =>
          prev ? { ...prev, ...msg.call } : prev
        );
        break;

      case "call_ended":
        setActiveCall((prev) => {
          if (prev) {
            const ended = {
              ...prev,
              status: "ended" as const,
              end_time: msg.end_time,
              duration_seconds: msg.duration_seconds,
            };
            setFinalCall(ended);
            return null;
          }
          return prev;
        });
        setCallEnded(true);
        break;
    }
  }, []);

  const wsUrl = useMemo(() => getWsUrl(), []);
  const { readyStateLabel, sendJson } = useWebSocket(wsUrl, {
    onMessage: handleMessage,
    reconnect: true,
    maxReconnectAttempts: 3,
  });

  // ── Live duration timer ──
  useEffect(() => {
    if (activeCall && activeCall.status === "active") {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [activeCall?.id, activeCall?.status]);

  // ── Reset timer for new calls ──
  useEffect(() => {
    if (activeCall?.start_time) {
      try {
        const start = new Date(activeCall.start_time).getTime();
        setElapsed(Math.floor((Date.now() - start) / 1000));
      } catch {
        setElapsed(0);
      }
    }
  }, [activeCall?.id]);

  function formatElapsed(totalSeconds: number): string {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function handleEndCall() {
    sendJson({ type: "end_call", call_id: activeCall?.id });
  }

  // ── Connection status indicator ──
  const isConnected = readyStateLabel === "open";
  const callerName =
    activeCall?.caller_name || activeCall?.caller_number || undefined;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top bar */}
      <header className="bg-white shadow-sm border-b px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate("/calls")}>
            ← Back
          </Button>
          <h1 className="text-lg font-bold text-gray-900">Live Monitor</h1>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant={isConnected ? "green" : "default"}
            pulse={isConnected}
          >
            {isConnected ? "Live" : "Backend offline"}
          </Badge>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col lg:flex-row gap-0">
        {/* ── Left Panel: Call Metadata ── */}
        <aside className="lg:w-80 xl:w-96 bg-white border-r border-gray-200 flex-shrink-0 overflow-y-auto">
          {/* Active call card */}
          {activeCall && (
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                  Active Call
                </h2>
                <CallStatusBadge status={activeCall.status} />
              </div>

              <div className="space-y-3">
                {/* Caller */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Caller</p>
                  <p className="font-semibold text-gray-900">
                    {activeCall.caller_name || activeCall.caller_number}
                  </p>
                  {activeCall.caller_name && (
                    <p className="text-sm text-gray-500">
                      {activeCall.caller_number}
                    </p>
                  )}
                </div>

                {/* Profile */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Profile</p>
                  <p className="font-medium text-gray-900">
                    {activeCall.profile_name || "Default"}
                  </p>
                </div>

                {/* Duration */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Duration</p>
                  <p className="text-2xl font-mono font-bold text-blue-600 tabular-nums">
                    {formatElapsed(elapsed)}
                  </p>
                </div>

                {/* Transcript count */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Messages</p>
                  <p className="text-xl font-bold text-gray-900">
                    {transcript.length}
                  </p>
                </div>
              </div>

              {/* End Call Button */}
              <div className="mt-4">
                <Button
                  variant="danger"
                  className="w-full"
                  onClick={handleEndCall}
                >
                  End Call
                </Button>
              </div>
            </div>
          )}

          {/* Idle state */}
          {!activeCall && !callEnded && (
            <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
              <div className="relative mb-6">
                <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                    />
                  </svg>
                </div>
                <span className="absolute top-0 right-0 flex h-4 w-4">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-4 w-4 bg-green-500" />
                </span>
              </div>
              <h3 className="text-lg font-semibold text-gray-700 mb-1">
                {isConnected ? "Waiting for Calls" : "Backend Not Connected"}
              </h3>
              <p className="text-sm text-gray-500 max-w-xs">
                {isConnected
                  ? "The system is ready. When a call arrives, the live transcript will appear here."
                  : "Start the backend server on port 8000 to receive live calls and transcripts."}
              </p>
              {!isConnected && (
                <Spinner className="mt-4 h-6 w-6" />
              )}
            </div>
          )}

          {/* Call ended summary */}
          {callEnded && finalCall && (
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                  Call Ended
                </h2>
                <CallStatusBadge status="ended" />
              </div>

              <div className="space-y-3">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Caller</p>
                  <p className="font-semibold text-gray-900">
                    {finalCall.caller_name || finalCall.caller_number}
                  </p>
                </div>

                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Duration</p>
                  <p className="text-xl font-bold text-gray-900">
                    {formatElapsed(
                      finalCall.duration_seconds || elapsed
                    )}
                  </p>
                </div>

                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Messages</p>
                  <p className="text-xl font-bold text-gray-900">
                    {transcript.length}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <Button
                  className="w-full"
                  onClick={() => navigate(`/calls/${finalCall.id}`)}
                >
                  View Full Detail
                </Button>
              </div>
            </div>
          )}

          {/* Recent transcript quick stats */}
          {transcript.length > 0 && (
            <div className="p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Speaker Breakdown
              </h3>
              <div className="flex gap-4">
                <div className="flex-1 bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-xs text-blue-600 font-medium">AI</p>
                  <p className="text-xl font-bold text-blue-700">
                    {transcript.filter((t) => t.speaker === "ai").length}
                  </p>
                </div>
                <div className="flex-1 bg-gray-100 rounded-lg p-3 text-center">
                  <p className="text-xs text-gray-600 font-medium">Human</p>
                  <p className="text-xl font-bold text-gray-700">
                    {transcript.filter((t) => t.speaker === "human").length}
                  </p>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* ── Right Panel: Live Transcript ── */}
        <section className="flex-1 flex flex-col min-h-0 bg-white">
          <div className="px-6 py-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              {activeCall
                ? "Live Transcript"
                : callEnded
                  ? "Call Transcript"
                  : "Transcript"}
            </h2>
          </div>
          <div className="flex-1 overflow-hidden">
            <TranscriptView
              entries={transcript}
              isLive={!!activeCall}
              loading={false}
              callerName={callerName}
            />
          </div>
        </section>
      </main>
    </div>
  );
}
