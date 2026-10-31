import { useParams } from "react-router-dom";
import { api, type SchemeResult } from "../api/client";
import { SchemeLinks } from "../components/SchemeLinks";
import { ErrorNote, Loading } from "../components/States";
import { OutcomeChip, StatusChip } from "../components/StatusChip";
import { useLoad } from "../hooks/useLoad";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";

async function findResult(sessionId: string | null, schemeId: string): Promise<SchemeResult | null> {
  if (!sessionId) return null;
  const { groups } = await api.results(sessionId).catch(() => ({ groups: null }));
  if (!groups) return null;
  const all = [...(groups.potentially_eligible ?? []), ...(groups.cannot_determine ?? []), ...(groups.not_eligible ?? [])];
  return all.find((result) => result.scheme_id === schemeId) ?? null;
}

export function Scheme() {
  const { t, lang } = useT();
  const { id = "" } = useParams();
  const { sessionId } = useSession();
  const { data, error, loading, reload } = useLoad(
    async () => ({ scheme: await api.scheme(id), result: await findResult(sessionId, id) }),
    [id, sessionId, lang],
  );

  const scheme = data?.scheme;
  const result = data?.result;

  return (
    <section className="container-page py-8">
      {loading && !data && <Loading />}
      {error && <ErrorNote onRetry={reload} />}
      {scheme && (
        <div className="flex flex-col gap-6">
          <header className="flex flex-col gap-3">
            {result && <div><StatusChip status={result.status} /></div>}
            <h1 className="page-title">{scheme.name.en}</h1>
            <p className="text-muted">{scheme.department}</p>
            <p className="max-w-2xl text-(length:--text-lead) text-ink-2">{scheme.summary}</p>
            <p className="well max-w-2xl"><strong>{t("scheme.benefits")}</strong> {scheme.benefits}</p>
            <SchemeLinks source={scheme.source} applicationUrl={scheme.application_url ?? null} />
          </header>

          <section aria-labelledby="rules">
            <h2 id="rules" className="section-title">{t("scheme.rules")}</h2>
            <div className="flex flex-col border-t-2 border-ink">
              {(result?.rules ?? scheme.rules.map((rule) => ({ ...rule, explanation: "", outcome: null }))).map((rule) => (
                <article key={rule.rule_id} className={rule.outcome ? "rule-row rule-row-status" : "rule-row"}>
                  {rule.outcome && <div><OutcomeChip outcome={rule.outcome} /></div>}
                  <div className="flex min-w-0 flex-col gap-2">
                    {rule.explanation && rule.outcome !== "MANUAL" && <p className="font-medium text-ink">{rule.explanation}</p>}
                    <blockquote className="excerpt">{rule.source_excerpt}</blockquote>
                    <a href={scheme.source.url} target="_blank" rel="noreferrer" className="self-start text-sm">
                      {t("scheme.source")}
                    </a>
                  </div>
                </article>
              ))}
            </div>
          </section>

          {scheme.unmapped_conditions && scheme.unmapped_conditions.length > 0 && (
            <section aria-labelledby="other" className="panel">
              <h2 id="other" className="row-title">{t("scheme.other_conditions")}</h2>
              <ul className="mt-2 mb-0 pl-5">
                {scheme.unmapped_conditions.map((condition) => (
                  <li key={condition}>{condition}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
