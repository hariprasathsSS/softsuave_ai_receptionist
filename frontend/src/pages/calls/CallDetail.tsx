import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import type { Call, TranscriptEntry } from "../../types";
import { fetchCall, fetchCallTranscript } from "../../api/calls";
import { Button, Badge, Spinner } from "../../components/ui/Button";
import CallStatusBadge from "../../components/CallStatusBadge";
import TranscriptView from "../../components/TranscriptView";
import { formatDateTime, formatDuration } from "../../utils/format";

export default function CallDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [call, setCall] = useState<Call | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [loadingCall, setLoadingCall] = useState(true);
  const [loadingTranscript, setLoadingTranscript] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    // Fetch call metadata
    setLoadingCall(true);
    fetchCall(id)
      .then((data) => {
        if (!cancelled) setCall(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err?.response?.status === 404
              ? "Call not found"
              : err?.response?.data?.detail || err.message || "Failed to load call"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingCall(false);
      });

    // Fetch transcript separately
    setLoadingTranscript(true);
    fetchCallTranscript(id)
      .then((data) => {
        if (!cancelled) setTranscript(data);
      })
      .catch(() => {
        // Transcript may not exist — that's OK
        if (!cancelled) setTranscript([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingTranscript(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  // Error state
  if (error && !call) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="text-center py-20">
          <div className="text-red-500 text-lg font-medium mb-2">{error}</div>
          <Button variant="secondary" onClick={() => navigate("/calls")}>
            Back to Calls
          </Button>
        </div>
      </div>
    );
  }

  // Loading state
  if (loadingCall) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" onClick={() => navigate("/calls")}>
          ← Back
        </Button>
        <h1 className="text-xl font-bold text-gray-900">Call Detail</h1>
        {call && <CallStatusBadge status={call.status} />}
      </div>

      {/* Metadata Card */}
      {call && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <MetaItem
              label="Caller"
              value={call.caller_name || call.caller_number}
              sub={call.caller_name ? call.caller_number : undefined}
            />
            <MetaItem
              label="Profile"
              value={call.profile_name || "Default"}
            />
            <MetaItem label="Direction" value={call.direction === "inbound" ? "Inbound" : "Outbound"} />
            <MetaItem label="Start Time" value={formatDateTime(call.start_time)} />
            <MetaItem label="End Time" value={formatDateTime(call.end_time)} />
            <MetaItem label="Duration" value={formatDuration(call.duration_seconds)} />
          </div>

          {/* Recording */}
          {call.recording_url && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm font-medium text-gray-700 mb-2">
                Recording
              </p>
              <audio controls className="w-full max-w-md" src={call.recording_url}>
                Your browser does not support audio playback.
              </audio>
            </div>
          )}
        </div>
      )}

      {/* Transcript Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Transcript</h2>
          <Badge variant={transcript.length > 0 ? "green" : "default"}>
            {transcript.length} messages
          </Badge>
        </div>
        <TranscriptView
          entries={transcript}
          loading={loadingTranscript}
          callerName={call?.caller_name || call?.caller_number || undefined}
        />
      </div>
    </div>
  );
}

function MetaItem({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-sm font-medium text-gray-900 mt-0.5">{value}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </div>
  );
}
