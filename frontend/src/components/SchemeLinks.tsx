import { ExternalLink } from "lucide-react";
import { useT } from "../hooks/useT";

interface Props {
  source: { url: string; title: string; retrieved_on: string };
  applicationUrl: string | null;
}

export function SchemeLinks({ source, applicationUrl }: Props) {
  const { t } = useT();

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-ink-2">
      <a href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1">
        {t("scheme.source")}
        <ExternalLink size={14} aria-hidden="true" />
      </a>
      <span className="text-muted">{t("scheme.retrieved", { date: source.retrieved_on })}</span>
      {applicationUrl ? (
        <a href={applicationUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium">
          {t("scheme.apply")}
          <ExternalLink size={14} aria-hidden="true" />
        </a>
      ) : (
        <span className="text-muted">{t("scheme.offline")}</span>
      )}
    </div>
  );
}
