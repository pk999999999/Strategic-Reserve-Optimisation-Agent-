import { Loader2 } from "lucide-react";

export interface LoadingIndicatorProps {
  
  label?: string;
  
  fullHeight?: boolean;
  className?: string;
}

export function LoadingIndicator({
  label = "Loadingâ€¦",
  fullHeight = false,
  className,
}: LoadingIndicatorProps) {
  const wrapper = [
    "flex items-center justify-center gap-2 text-sm text-slate-500",
    fullHeight ? "h-full min-h-[120px]" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={wrapper} role="status" aria-live="polite">
      <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export default LoadingIndicator;
