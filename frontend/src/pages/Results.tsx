import { Link, useSearchParams } from "react-router-dom";
import { api, type SchemeStatus } from "../api/client";
import { AskPanel } from "../components/AskPanel";
import { SchemeCard } from "../components/SchemeCard";
import { Empty, ErrorNote, Loading, NoSession, PageHead } from "../components/States";
import { StatusChip } from "../components/StatusChip";
import { useLoad } from "../hooks/useLoad";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";

const TABS: SchemeStatus[] = ["potentially_eligible", "cannot_determine", "not_eligible"];

export function Results() {
  const { t, lang } = useT();
  const { sessionId } = useSession();
  const [params, setParams] = useSearchParams();
  const { data, error, loading, reload } = useLoad(
    () => (sessionId ? api.results(sessionId) : Promise.resolve(null)),
    [sessionId, lang],
  );

  if (!sessionId) return <section className="container-page py-8"><NoSession /></section>;

  const tab = (TABS.find((name) => name === params.get("tab")) ?? "potentially_eligible") as SchemeStatus;
  const rows = data?.groups[tab] ?? [];

  return (
    <section className="container-page py-8">
      <PageHead title="page.results" lead="results.lead" />
      {loading && !data && <Loading />}
      {error && <ErrorNote onRetry={reload} />}

      {data && !data.confirmed && (
        <Empty message="results.unconfirmed">
          <Link to="/confirm" className="btn btn-primary">
            {t("page.confirm")}
          </Link>
        </Empty>
      )}

      {data?.confirmed && (
        <>
          <div role="tablist" aria-label={t("page.results")} className="tabs">
            {TABS.map((name) => (
              <button
                key={name}
                role="tab"
                type="button"
                aria-selected={tab === name}
                className="tab"
                onClick={() => setParams({ tab: name }, { replace: true })}
              >
                <StatusChip status={name} />
                <span className="tab-count">{data.groups[name]?.length ?? 0}</span>
              </button>
            ))}
          </div>

          <div className="grid items-start gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,1fr)_340px]">
            <div role="tabpanel" className="flex min-w-0 flex-col">
              {rows.length === 0 && <div className="mt-6"><Empty message="results.empty" /></div>}
              {rows.map((result) => (
                <SchemeCard key={result.scheme_id} result={result} labels={data.labels} onChanged={reload} />
              ))}
            </div>

            <aside className="flex min-w-0 flex-col gap-3 lg:pt-6">
              <Link to="/documents" className="btn btn-primary">
                {t("results.to_plan")}
              </Link>
              <Link to="/packet" className="btn">
                {t("page.packet")}
              </Link>
              <AskPanel />
            </aside>
          </div>
        </>
      )}
    </section>
  );
}
