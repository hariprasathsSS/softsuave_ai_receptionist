import type { TranscriptSpeaker } from "../types";
import { cn } from "./ui/Button";
import { formatTime } from "../utils/format";

interface TranscriptBubbleProps {
  speaker: TranscriptSpeaker;
  text: string;
  timestamp: string;
  isLive?: boolean;
  callerName?: string;
}

export default function TranscriptBubble({
  speaker,
  text,
  timestamp,
  isLive,
  callerName,
}: TranscriptBubbleProps) {
  const isAI = speaker === "ai";

  return (
    <div
      className={cn(
        "flex gap-3 mb-4",
        isAI ? "justify-start" : "justify-end"
      )}
    >
      {/* AI Avatar */}
      {isAI && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm font-bold mt-1">
          AI
        </div>
      )}

      {/* Bubble */}
      <div className={cn("max-w-[75%]", isLive && "animate-slide-in")}>
        {/* Speaker label */}
        <div
          className={cn(
            "text-xs font-medium mb-1 px-1",
            isAI ? "text-blue-600" : "text-gray-600 text-right"
          )}
        >
          {isAI ? "AI Receptionist" : callerName || "Caller"}
        </div>

        {/* Message body */}
        <div
          className={cn(
            "px-4 py-2.5 rounded-2xl text-sm leading-relaxed",
            isAI
              ? "bg-gray-100 text-gray-800 rounded-tl-sm"
              : "bg-blue-600 text-white rounded-tr-sm"
          )}
        >
          {text}
        </div>

        {/* Timestamp */}
        <div
          className={cn(
            "text-xs text-gray-400 mt-1 px-1",
            !isAI && "text-right"
          )}
        >
          {formatTime(timestamp)}
        </div>
      </div>

      {/* Human Avatar */}
      {!isAI && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 text-sm font-bold mt-1">
          {callerName?.charAt(0)?.toUpperCase() || "C"}
        </div>
      )}
    </div>
  );
}
