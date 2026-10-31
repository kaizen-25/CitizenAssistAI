import { Printer } from "lucide-react";
import { api, type SchemeResult, type SchemeStatus } from "../api/client";
import { ErrorNote, Loading, NoSession, PageHead } from "../components/States";
import { StatusChip } from "../components/StatusChip";
import { UnlockPlan } from "../components/UnlockPlan";
import { useLoad } from "../hooks/useLoad";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";

const GROUPS: SchemeStatus[] = ["potentially_eligible", "cannot_determine", "not_eligible"];

export function Packet() {
  const { t, lang } = useT();
  const { sessionId } = useSession();
  const { data, error, loading, reload } = useLoad(
    () => (sessionId ? api.packet(sessionId) : Promise.resolve(null)),
    [sessionId, lang],
  );

  if (!sessionId) return <section className="container-page py-8"><NoSession /></section>;

  const docLabel = (id: string) => data?.labels.documents?.[id] ?? id;
  const all: SchemeResult[] = GROUPS.flatMap((status) => data?.groups[status] ?? []);
  const open = all.filter((scheme) => scheme.status !== "not_eligible");
  const sources = [...new Map(all.map((scheme) => [scheme.source.url, scheme.source])).values()];
  const heldDocs = [...new Set(open.flatMap((s) => s.documents.held ?? []))];
  const neededDocs = [...new Set(open.flatMap((s) => [...(s.documents.missing ?? []), ...(s.documents.unsure ?? [])]))];

  return (
    <section className="container-page packet py-8">
      <PageHead title="page.packet" lead="packet.lead" />
      {loading && !data && <Loading />}
      {error && <ErrorNote onRetry={reload} />}

      {data && (
        <div className="flex flex-col gap-6">
          <button type="button" className="btn btn-primary no-print self-start" onClick={() => window.print()}>
            <Printer size={18} aria-hidden="true" />
            {t("packet.print")}
          </button>

          <section>
            <h2 className="section-title">{t("packet.profile")}</h2>
            <dl className="m-0 grid gap-x-6 gap-y-1 sm:grid-cols-2">
              {Object.entries(data.profile).map(([field, entry]) => (
                <div key={field} className="flex justify-between gap-3 border-b border-rule py-1">
                  <dt className="text-muted">{entry.label}</dt>
                  <dd className="m-0 font-medium">{entry.display}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section>
            <h2 className="section-title">{t("packet.schemes")}</h2>
            <table className="table">
              <tbody>
                {all.map((scheme) => (
                  <tr key={scheme.scheme_id}>
                    <td className="font-medium">
                      {scheme.name}
                      <div className="text-sm font-normal break-all">{scheme.application_url ?? scheme.source.url}</div>
                    </td>
                    <td><StatusChip status={scheme.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="section-title">{t("packet.checklist")}</h2>
            <ul className="m-0 grid list-none gap-1 p-0 sm:grid-cols-2">
              {heldDocs.map((id) => <li key={id}>☑ {docLabel(id)}</li>)}
              {neededDocs.map((id) => <li key={id}>☐ {docLabel(id)}</li>)}
            </ul>
          </section>

          {(data.unlock.plan ?? []).length > 0 && (
            <section>
              <h2 className="section-title">{t("unlock.plan")}</h2>
              <UnlockPlan report={data.unlock} docLabel={docLabel} />
            </section>
          )}

          <section>
            <h2 className="section-title">{t("packet.sources")}</h2>
            <ul className="m-0 flex list-none flex-col gap-1 p-0 text-sm">
              {sources.map((source) => (
                <li key={source.url} className="break-all">
                  {source.title}: {source.url} ({t("scheme.retrieved", { date: source.retrieved_on })})
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="section-title">{t("packet.notes")}</h2>
            <div className="notes-box" aria-hidden="true" />
          </section>

          <p className="text-sm">{data.disclaimer}</p>
        </div>
      )}
    </section>
  );
}
