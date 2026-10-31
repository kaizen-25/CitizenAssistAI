import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Empty, ErrorNote, Loading, NoSession, PageHead } from "../components/States";
import { UnlockGraph } from "../components/UnlockGraph";
import { UnlockPlan } from "../components/UnlockPlan";
import { useLoad } from "../hooks/useLoad";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";

export function Documents() {
  const { t, lang } = useT();
  const { sessionId } = useSession();
  const { data, error, loading, reload } = useLoad(
    () => (sessionId ? api.packet(sessionId) : Promise.resolve(null)),
    [sessionId, lang],
  );

  if (!sessionId) return <section className="container-page py-8"><NoSession /></section>;

  const unlock = data?.unlock;
  const eligible = data?.groups.potentially_eligible ?? [];
  const docLabel = (id: string) => data?.labels.documents?.[id] ?? id;
  const nameOf = (id: string) => eligible.find((scheme) => scheme.scheme_id === id)?.name ?? id;
  const possible = [...new Set(eligible.flatMap((scheme) => scheme.documents.possibly_required ?? []))];

  return (
    <section className="container-page py-8">
      <PageHead title="page.documents" lead="unlock.lead" />
      {loading && !data && <Loading />}
      {error && <ErrorNote onRetry={reload} />}

      {data && unlock && (
        <div className="flex flex-col gap-8">
          {unlock.ready_now && unlock.ready_now.length > 0 && (
            <div className="panel">
              <h2 className="row-title">{t("unlock.ready_now")}</h2>
              <ul className="mt-2 mb-0 pl-5">
                {unlock.ready_now.map((id) => (
                  <li key={id}>
                    <Link to={`/scheme/${id}`}>{nameOf(id)}</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(unlock.plan ?? []).length === 0 && <Empty message="unlock.empty" />}

          {(unlock.plan ?? []).length > 0 && (
            <>
              <section aria-labelledby="plan">
                <h2 id="plan" className="section-title">{t("unlock.plan")}</h2>
                <UnlockPlan report={unlock} docLabel={docLabel} />
                {possible.length > 0 && (
                  <p className="mt-3 text-sm">{t("unlock.possibly", { docs: possible.map(docLabel).join(", ") })}</p>
                )}
              </section>

              <section aria-labelledby="ranking">
                <h2 id="ranking" className="section-title">{t("unlock.ranking")}</h2>
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead>
                      <tr>
                        <th scope="col">{t("unlock.rank")}</th>
                        <th scope="col">{t("unlock.document")}</th>
                        <th scope="col" className="num">{t("unlock.required_by")}</th>
                        <th scope="col" className="num">{t("unlock.only_blocker")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(unlock.ranking ?? []).map((entry) => (
                        <tr key={entry.document_id}>
                          <td className="font-medium">{entry.rank}</td>
                          <td className="font-medium">{entry.label}</td>
                          <td className="num">{entry.required_by.length}</td>
                          <td className="num">{entry.sole_blocker_for.length}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section aria-labelledby="graph">
                <h2 id="graph" className="section-title">{t("unlock.graph")}</h2>
                <UnlockGraph report={unlock} schemes={eligible} />
              </section>
            </>
          )}

          {(unlock.pending_info ?? []).length > 0 && (
            <section aria-labelledby="pending" className="panel">
              <h2 id="pending" className="row-title">{t("unlock.pending")}</h2>
              <p className="mt-1 text-sm text-muted">{t("unlock.pending_lead")}</p>
              <ul className="mt-2 mb-0 pl-5">
                {(unlock.pending_info ?? []).map((item) => (
                  <li key={item.scheme_id}>
                    <Link to={`/scheme/${item.scheme_id}`}>
                      {data.groups.cannot_determine?.find((s) => s.scheme_id === item.scheme_id)?.name ?? item.scheme_id}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div>
            <Link to="/packet" className="btn btn-primary">
              {t("page.packet")}
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
