import { useEffect, useRef } from "react";
import type { TranscriptEntry } from "../types";
import TranscriptBubble from "./TranscriptBubble";
import { Skeleton } from "./ui/Button";

interface TranscriptViewProps {
  entries: TranscriptEntry[];
  isLive?: boolean;
  callerName?: string;
  loading?: boolean;
}

export default function TranscriptView({
  entries,
  isLive,
  callerName,
  loading,
}: TranscriptViewProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new entries arrive in live mode
  useEffect(() => {
    if (isLive && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [entries.length, isLive]);

  // Loading state
  if (loading) {
    return (
      <div className="p-6 space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`flex gap-3 ${i % 2 === 0 ? "justify-end" : "justify-start"}`}
          >
            <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
            <div className="space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton
                className={`h-10 rounded-2xl ${i % 2 === 0 ? "w-48" : "w-64"}`}
              />
              <Skeleton className="h-2 w-12" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Empty state
  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <svg
          className="w-12 h-12 mb-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
        <p className="text-sm font-medium">No transcript available</p>
        <p className="text-xs mt-1">
          {isLive
            ? "Transcript will appear here as the conversation unfolds."
            : "This call has no recorded transcript."}
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-1 max-h-[70vh] overflow-y-auto transcript-scrollbar">
      {entries.map((entry) => (
        <TranscriptBubble
          key={entry.id || `${entry.sequence}-${entry.timestamp}`}
          speaker={entry.speaker}
          text={entry.text}
          timestamp={entry.timestamp}
          isLive={isLive}
          callerName={callerName}
        />
      ))}
      {/* Invisible element for auto-scroll anchoring */}
      <div ref={bottomRef} />
    </div>
  );
}
