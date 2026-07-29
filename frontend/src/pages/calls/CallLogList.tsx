import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { Call } from "../../types";
import { fetchCalls, type FetchCallsParams } from "../../api/calls";
import { Table, Badge, Spinner, Button } from "../../components/ui/Button";
import CallStatusBadge from "../../components/CallStatusBadge";
import { formatDuration, formatTime } from "../../utils/format";

type StatusFilter = "all" | "active" | "ended" | "missed";

const FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "ended", label: "Ended" },
  { value: "missed", label: "Missed" },
];

export default function CallLogList() {
  const navigate = useNavigate();
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params: FetchCallsParams = { page, limit: 20 };
    if (statusFilter !== "all") {
      params.status = statusFilter;
    }

    fetchCalls(params)
      .then((res) => {
        if (!cancelled) {
          setCalls(res.items);
          setTotalPages(res.pages);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err.message || "Failed to load calls");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [statusFilter, page]);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Call Logs</h1>
          <p className="text-sm text-gray-500 mt-1">
            Browse and review past calls and transcripts
          </p>
        </div>
        <Button onClick={() => navigate("/calls/live")}>
          Live Monitor
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => {
              setStatusFilter(opt.value);
              setPage(1);
            }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusFilter === opt.value
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8" />
        </div>
      ) : (
        <>
          <Table<Call>
            columns={[
              {
                key: "caller_number",
                header: "Caller",
                render: (row) => (
                  <div>
                    <p className="font-medium text-gray-900">
                      {row.caller_name || row.caller_number}
                    </p>
                    {row.caller_name && (
                      <p className="text-xs text-gray-500">{row.caller_number}</p>
                    )}
                  </div>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (row) => <CallStatusBadge status={row.status} />,
              },
              {
                key: "profile_name",
                header: "Profile",
                render: (row) => (
                  <span className="text-gray-600">
                    {row.profile_name || "—"}
                  </span>
                ),
              },
              {
                key: "start_time",
                header: "Time",
                render: (row) => (
                  <span className="text-gray-600">
                    {formatTime(row.start_time)}
                  </span>
                ),
              },
              {
                key: "duration",
                header: "Duration",
                render: (row) => (
                  <span className="text-gray-600">
                    {formatDuration(row.duration_seconds)}
                  </span>
                ),
              },
              {
                key: "transcript_count",
                header: "Transcript",
                render: (row) => (
                  <Badge
                    variant={row.transcript_count > 0 ? "green" : "default"}
                  >
                    {row.transcript_count} msgs
                  </Badge>
                ),
              },
            ]}
            data={calls}
            rowKey={(row) => row.id}
            onRowClick={(row) => navigate(`/calls/${row.id}`)}
            emptyMessage="No calls found matching the selected filter."
          />

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-6">
              <Button
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
