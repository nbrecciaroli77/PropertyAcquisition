import clsx from "clsx";
import { AlertOctagon, Inbox, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
  "data-testid": testId = "empty-state",
}: {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <div className={clsx("card flex flex-col items-start gap-3 p-6", className)} data-testid={testId} role="status">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-eucalyptus-soft text-eucalyptus-deep">
        {icon ?? <Inbox className="h-5 w-5" aria-hidden="true" />}
      </span>
      <div>
        <h3 className="text-h3 font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-muted max-w-prose">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something didn't load",
  description,
  onRetry,
  className,
  "data-testid": testId = "error-state",
}: {
  title?: string;
  description: string;
  onRetry?: () => void;
  className?: string;
  "data-testid"?: string;
}) {
  return (
    <div className={clsx("card flex flex-col items-start gap-3 border-risk/40 p-6", className)} data-testid={testId} role="alert">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-risk-soft text-risk">
        <AlertOctagon className="h-5 w-5" aria-hidden="true" />
      </span>
      <div>
        <h3 className="text-h3 font-semibold text-risk">{title}</h3>
        <p className="mt-1 text-sm text-muted max-w-prose">{description}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />} data-testid="error-state-retry">
          Try again
        </Button>
      )}
    </div>
  );
}

export function Skeleton({ className, label = "Loading" }: { className?: string; label?: string }) {
  return (
    <div className={clsx("skeleton rounded-md", className)} role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}</span>
    </div>
  );
}

export function PropertyCardSkeleton() {
  return (
    <div className="card overflow-hidden" data-testid="property-card-skeleton">
      <Skeleton className="h-40 rounded-none" />
      <div className="space-y-3 p-4">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-4 w-1/2" />
        <div className="flex gap-2">
          <Skeleton className="h-11 w-11 rounded-full" />
          <Skeleton className="h-11 w-11 rounded-full" />
        </div>
      </div>
    </div>
  );
}
