import { AlertTriangle } from "lucide-react";

export interface ErrorMessageProps {
  
  module: string;
  
  message: string;
  
  onRetry?: () => void;
  className?: string;
}

export function ErrorMessage({ module, message, onRetry, className }: ErrorMessageProps) {
  const wrapper = [
    "flex flex-col gap-2 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={wrapper} role="alert">
      <div className="flex items-center gap-2 font-semibold text-rose-700">
        <AlertTriangle className="h-4 w-4" aria-hidden />
        <span className="uppercase tracking-wide">{module}</span>
      </div>
      <p className="text-rose-600">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 self-start rounded-md border border-rose-300 px-3 py-1 text-xs font-medium text-rose-700 transition hover:bg-rose-100"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export default ErrorMessage;
