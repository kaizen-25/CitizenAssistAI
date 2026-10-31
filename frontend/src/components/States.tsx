import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useT, type StringKey } from "../hooks/useT";

export function Loading() {
  const { t } = useT();
  return (
    <div role="status" aria-label={t("state.loading")} className="flex flex-col gap-3">
      <div className="skeleton h-8 w-2/3" />
      <div className="skeleton h-24" />
      <div className="skeleton h-24" />
    </div>
  );
}

export function ErrorNote({ onRetry }: { onRetry?: () => void }) {
  const { t } = useT();
  return (
    <div role="alert" className="panel flex flex-col items-start gap-3">
      <p>{t("state.error")}</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          {t("state.retry")}
        </button>
      )}
    </div>
  );
}

export function NoSession() {
  const { t } = useT();
  return (
    <Empty message="state.no_session">
      <Link to="/assess" className="btn btn-primary">
        {t("landing.action")}
      </Link>
    </Empty>
  );
}

export function Empty({ message, children }: { message: StringKey; children?: ReactNode }) {
  const { t } = useT();
  return (
    <div className="panel flex flex-col items-start gap-3">
      <p>{t(message)}</p>
      {children}
    </div>
  );
}

export function PageHead({ title, lead }: { title: StringKey; lead?: StringKey }) {
  const { t } = useT();
  return (
    <header className="mb-6 flex flex-col gap-2">
      <h1 className="page-title">{t(title)}</h1>
      {lead && <p className="max-w-2xl text-ink-2">{t(lead)}</p>}
    </header>
  );
}
