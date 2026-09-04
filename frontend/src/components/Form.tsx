import clsx from "clsx";
import type { ChangeEvent, ReactNode } from "react";

const controlClass =
  "h-11 w-full min-w-0 rounded-md border border-border bg-surface px-3 text-sm placeholder:text-muted disabled:bg-canvas disabled:text-muted";

function Wrapper({
  id,
  label,
  helper,
  error,
  children,
  className,
}: {
  id: string;
  label: string;
  helper?: ReactNode;
  error?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("min-w-0", className)}>
      <label htmlFor={id} className="mb-1 block text-sm font-semibold">
        {label}
      </label>
      {children}
      {helper && !error && (
        <p id={`${id}-help`} className="mt-1 text-xs text-muted">
          {helper}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1 flex gap-1 text-xs font-semibold text-risk" data-testid={`${id}-error`}>
          <span aria-hidden="true">!</span>
          {error}
        </p>
      )}
    </div>
  );
}

export interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  helper?: ReactNode;
  error?: string;
  placeholder?: string;
  autoComplete?: string;
  inputMode?: "text" | "numeric" | "email" | "decimal";
  required?: boolean;
  disabled?: boolean;
  className?: string;
  testId?: string;
}

export function TextField({
  id,
  label,
  value,
  onChange,
  type = "text",
  helper,
  error,
  placeholder,
  autoComplete,
  inputMode,
  required,
  disabled,
  className,
  testId,
}: TextFieldProps) {
  return (
    <Wrapper id={id} label={label} helper={helper} error={error} className={className}>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        placeholder={placeholder}
        autoComplete={autoComplete}
        inputMode={inputMode}
        required={required}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : helper ? `${id}-help` : undefined}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
        className={clsx(controlClass, error && "border-risk")}
        data-testid={testId ?? id}
      />
    </Wrapper>
  );
}

export function NumberField({
  id,
  label,
  value,
  onChange,
  suffix,
  helper,
  error,
  disabled,
  className,
  testId,
}: {
  id: string;
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  suffix?: string;
  helper?: ReactNode;
  error?: string;
  disabled?: boolean;
  className?: string;
  testId?: string;
}) {
  return (
    <Wrapper id={id} label={label} helper={helper} error={error} className={className}>
      <div className="flex items-center gap-2">
        <input
          id={id}
          name={id}
          type="number"
          min={0}
          value={value === null ? "" : String(value)}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : helper ? `${id}-help` : undefined}
          onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          placeholder="Unknown"
          className={clsx(controlClass, error && "border-risk")}
          data-testid={testId ?? id}
        />
        {suffix && <span className="shrink-0 text-sm text-muted">{suffix}</span>}
      </div>
    </Wrapper>
  );
}

export function SelectField<T extends string>({
  id,
  label,
  value,
  onChange,
  options,
  helper,
  error,
  disabled,
  className,
  testId,
}: {
  id: string;
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
  helper?: ReactNode;
  error?: string;
  disabled?: boolean;
  className?: string;
  testId?: string;
}) {
  return (
    <Wrapper id={id} label={label} helper={helper} error={error} className={className}>
      <select
        id={id}
        name={id}
        value={value}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : helper ? `${id}-help` : undefined}
        onChange={(e) => onChange(e.target.value as T)}
        className={clsx(controlClass, "pr-8", error && "border-risk")}
        data-testid={testId ?? id}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Wrapper>
  );
}

export function FormNotice({
  tone = "info",
  children,
  testId,
}: {
  tone?: "info" | "error" | "success";
  children: ReactNode;
  testId?: string;
}) {
  const tones = {
    info: "border-navy/20 bg-navy-soft text-navy",
    error: "border-risk/40 bg-risk-soft text-risk",
    success: "border-eucalyptus/40 bg-eucalyptus-soft text-eucalyptus-deep",
  } as const;
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={clsx("rounded-md border px-3 py-2 text-sm", tones[tone])}
      data-testid={testId}
    >
      {children}
    </p>
  );
}
