import type { ReactNode } from "react";
import { BrandMark, ConceptBadge } from "../../components/Brand";

export function AuthLayout({
  eyebrow,
  title,
  description,
  children,
  footer,
  testId,
}: {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  testId: string;
}) {
  return (
    <div className="mx-auto w-full max-w-[560px] px-4 py-10 md:py-16" data-testid={testId}>
      <div className="rise-in">
        <div className="flex items-center gap-3">
          <BrandMark className="h-10 w-10" />
          <ConceptBadge />
        </div>
        <p className="label mt-8 text-eucalyptus-deep">{eyebrow}</p>
        <h1 className="mt-1 text-display">{title}</h1>
        {description && <p className="mt-3 text-muted">{description}</p>}
        <div className="mt-8">{children}</div>
        {footer && <div className="mt-6 text-sm text-muted">{footer}</div>}
      </div>
    </div>
  );
}
