import type { CallStatus } from "../types";
import { Badge } from "./ui/Button";

interface CallStatusBadgeProps {
  status: CallStatus;
}

const statusConfig: Record<
  CallStatus,
  { label: string; variant: "yellow" | "green" | "default" | "red" | "blue"; pulse: boolean }
> = {
  ringing: { label: "Ringing", variant: "yellow", pulse: true },
  active: { label: "In Progress", variant: "green", pulse: true },
  ended: { label: "Ended", variant: "default", pulse: false },
  missed: { label: "Missed", variant: "red", pulse: false },
  voicemail: { label: "Voicemail", variant: "blue", pulse: false },
};

export default function CallStatusBadge({ status }: CallStatusBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.ended;
  return (
    <Badge variant={config.variant} pulse={config.pulse}>
      {config.label}
    </Badge>
  );
}
