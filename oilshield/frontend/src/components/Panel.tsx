import type { ComponentType, ReactNode } from "react";
import { motion } from "framer-motion";

export type PanelAccent = "teal" | "amber" | "rose" | "emerald" | "violet" | "sky";

const ACCENT_TEXT: Record<PanelAccent, string> = {
  teal: "text-teal-600",
  amber: "text-amber-600",
  rose: "text-rose-600",
  emerald: "text-emerald-600",
  violet: "text-violet-600",
  sky: "text-sky-600",
};

const ACCENT_LINE: Record<PanelAccent, string> = {
  teal: "via-teal-500/60",
  amber: "via-amber-500/60",
  rose: "via-rose-500/60",
  emerald: "via-emerald-500/60",
  violet: "via-violet-500/60",
  sky: "via-sky-500/60",
};

export interface PanelProps {
  title?: string;
  subtitle?: string;
  
  icon?: ComponentType<{ className?: string }>;
  
  actions?: ReactNode;
  children?: ReactNode;
  
  ariaLabel?: string;
  
  accent?: PanelAccent;
  
  motionDelay?: number;
  className?: string;
  bodyClassName?: string;
}

export function Panel({
  title,
  subtitle,
  icon: Icon,
  actions,
  children,
  ariaLabel,
  accent = "teal",
  motionDelay = 0,
  className,
  bodyClassName,
}: PanelProps) {
  const hasHeader = Boolean(title || subtitle || Icon || actions);

  return (
    <motion.section
      aria-label={ariaLabel ?? title}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: motionDelay, ease: [0.22, 1, 0.36, 1] }}
      className={`relative flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel ${className ?? ""}`}
    >
      {/* Accent gradient hairline across the very top of the card. */}
      <div
        aria-hidden
        className={`pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent ${ACCENT_LINE[accent]} to-transparent`}
      />

      {hasHeader && (
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-2.5">
            {Icon && <Icon className={`h-5 w-5 shrink-0 ${ACCENT_TEXT[accent]}`} aria-hidden />}
            <div>
              {title && (
                <h2 className="font-display text-sm font-semibold tracking-tight text-slate-900">
                  {title}
                </h2>
              )}
              {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
            </div>
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={`flex-1 p-5 ${bodyClassName ?? ""}`}>{children}</div>
    </motion.section>
  );
}

export default Panel;
