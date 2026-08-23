import type { RiskBand } from "../types";
import { bandLabel, formatScore } from "../lib";

export interface StatusBadgeProps {
  band: RiskBand;
  
  score?: number;
  
  size?: "sm" | "md";
  className?: string;
}

const BAND_TEXT: Record<RiskBand, string> = {
  low: "text-emerald-700",
  elevated: "text-amber-600",
  high: "text-rose-700",
};

const LABEL_SIZE: Record<NonNullable<StatusBadgeProps["size"]>, string> = {
  sm: "text-[10px]",
  md: "text-[11px]",
};

const SCORE_SIZE: Record<NonNullable<StatusBadgeProps["size"]>, string> = {
  sm: "text-xs",
  md: "text-sm",
};

export function StatusBadge({ band, score, size = "md", className }: StatusBadgeProps) {
  const classes = ["inline-flex items-center gap-1.5", BAND_TEXT[band], className ?? ""]
    .filter(Boolean)
    .join(" ");

  return (
    <span className={classes}>
      <span className={`font-semibold uppercase tracking-wider ${LABEL_SIZE[size]}`}>
        {bandLabel(band)}
      </span>
      {score !== undefined && (
        <span className={`font-mono font-bold leading-none ${SCORE_SIZE[size]}`}>
          {formatScore(score)}
        </span>
      )}
    </span>
  );
}

export default StatusBadge;
