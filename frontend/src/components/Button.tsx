import clsx from "clsx";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { Link } from "react-router-dom";

type Variant = "primary" | "secondary" | "tertiary" | "success" | "neutral" | "destructive";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary: "bg-navy text-white hover:bg-charcoal active:translate-y-px",
  success: "bg-eucalyptus-deep text-white hover:brightness-95 active:translate-y-px",
  secondary: "bg-surface text-navy border border-border hover:border-navy hover:bg-canvas-deep",
  neutral: "bg-canvas-deep text-navy hover:bg-stone",
  tertiary: "bg-transparent text-eucalyptus-deep hover:underline underline-offset-4",
  destructive: "bg-surface text-risk border border-risk/40 hover:bg-risk-soft",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-3 text-sm gap-1.5",
  md: "h-11 px-4 text-[15px] gap-2",
  lg: "h-12 px-6 text-base gap-2",
};

const baseClass =
  "inline-flex items-center justify-center rounded-md font-semibold transition-[background-color,border-color,transform,filter] duration-150 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:translate-y-0 whitespace-nowrap";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", icon, className, children, type = "button", ...rest },
  ref,
) {
  return (
    <button ref={ref} type={type} className={clsx(baseClass, variants[variant], sizes[size], className)} {...rest}>
      {icon}
      {children}
    </button>
  );
});

export interface ButtonLinkProps {
  to: string;
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
  className?: string;
  children: ReactNode;
  "data-testid"?: string;
}

export const ButtonLink = forwardRef<HTMLAnchorElement, ButtonLinkProps>(function ButtonLink(
  { to, variant = "primary", size = "md", icon, className, children, ...rest },
  ref,
) {
  return (
    <Link ref={ref} to={to} className={clsx(baseClass, variants[variant], sizes[size], className)} {...rest}>
      {icon}
      {children}
    </Link>
  );
});
