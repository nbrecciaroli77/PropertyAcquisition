import clsx from "clsx";
import { Link } from "react-router-dom";

export function BrandMark({ className, light = false }: { className?: string; light?: boolean }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className={clsx("h-9 w-9 shrink-0", className)}>
      <path
        d="M32 8 L52 19 V45 L32 56 L12 45 V19 Z"
        fill="none"
        stroke={light ? "#F7F3EC" : "#102A36"}
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path d="M32 17 C41 24 43 35 32 47 C21 35 23 24 32 17 Z" fill="#6F8F7A" />
      <path d="M32 21 V47" stroke={light ? "#F7F3EC" : "#FFFFFF"} strokeWidth="2" />
    </svg>
  );
}

export function Wordmark({
  to = "/",
  light = false,
  compact = false,
}: {
  to?: string;
  light?: boolean;
  compact?: boolean;
}) {
  return (
    <Link
      to={to}
      data-testid="brand-wordmark"
      className={clsx("inline-flex items-center gap-3 rounded-md", light ? "text-white" : "text-navy")}
      aria-label="Property Acquisition — home"
    >
      <BrandMark light={light} />
      {!compact && <span className="font-semibold text-[19px] leading-6 tracking-tight">Property Acquisition</span>}
    </Link>
  );
}

export function ConceptBadge({ className }: { className?: string }) {
  return (
    <span
      data-testid="working-concept-badge"
      className={clsx(
        "inline-flex items-center rounded-sm border border-eucalyptus-deep/40 px-2 py-0.5 text-label uppercase text-eucalyptus-deep",
        className,
      )}
    >
      Working concept
    </span>
  );
}
