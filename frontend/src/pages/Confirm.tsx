import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type AnswerValue, type Question } from "../api/client";
import { QuestionForm } from "../components/QuestionForm";
import { ErrorNote, Loading, NoSession, PageHead } from "../components/States";
import { useLoad } from "../hooks/useLoad";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";

export function Confirm() {
  const { t, lang } = useT();
  const { sessionId } = useSession();
  const navigate = useNavigate();
  const [editing, setEditing] = useState<Question | null>(null);
  const [busy, setBusy] = useState(false);

  const { data, error, loading, reload } = useLoad(
    () => (sessionId ? api.results(sessionId) : Promise.resolve(null)),
    [sessionId, lang],
  );

  if (!sessionId) return <section className="container-page py-8"><NoSession /></section>;

  const save = async (value: AnswerValue) => {
    if (!editing) return;
    await api.answer(sessionId, editing.field_id, value);
    setEditing(null);
    reload();
  };

  const confirm = async () => {
    setBusy(true);
    await api.confirm(sessionId);
    navigate("/results");
  };

  return (
    <section className="container-page py-8">
      <PageHead title="page.confirm" lead="confirm.lead" />
      {loading && !data && <Loading />}
      {error && <ErrorNote onRetry={reload} />}
      {data && (
        <div className="flex max-w-2xl flex-col gap-4">
          <dl className="panel m-0 flex flex-col">
            {Object.entries(data.profile).map(([field, entry]) => (
              <div key={field} className={`readback ${entry.source === "extracted" ? "readback-extracted" : ""}`}>
                <dt className="text-sm text-muted">
                  {entry.label}
                  {entry.source === "extracted" && <span className="ml-2 font-medium text-ink">{t("confirm.extracted")}</span>}
                </dt>
                <dd className="m-0 flex items-center justify-between gap-3 font-medium">
                  {entry.display}
                  <button type="button" className="link-button" onClick={() => api.question(sessionId, field).then(setEditing)}>
                    {t("confirm.change")}
                  </button>
                </dd>
              </div>
            ))}
          </dl>
          {editing && (
            <div className="panel">
              <QuestionForm question={editing} onAnswer={save} />
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn btn-primary" disabled={busy} onClick={confirm}>
              {t("confirm.action")}
            </button>
            <Link to="/assess" className="btn">
              {t("confirm.restart")}
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
