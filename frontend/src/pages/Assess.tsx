import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type AnswerValue, type ChecklistItem, type DocumentAnswer, type Profile, type Question } from "../api/client";
import { QuestionForm } from "../components/QuestionForm";
import { ErrorNote, Loading, PageHead } from "../components/States";
import { useHealth } from "../hooks/useHealth";
import { useSession } from "../hooks/useSession";
import { useT, type StringKey } from "../hooks/useT";

const DOCUMENT_ANSWERS: { value: DocumentAnswer; label: StringKey }[] = [
  { value: "have", label: "documents.have" },
  { value: "missing", label: "documents.missing" },
  { value: "unsure", label: "documents.unsure" },
];

export function Assess() {
  const { t, lang } = useT();
  const { sessionId, setSessionId } = useSession();
  const navigate = useNavigate();

  const [question, setQuestion] = useState<Question | null>(null);
  const [profile, setProfile] = useState<Profile>({});
  const [answered, setAnswered] = useState(0);
  const [stage, setStage] = useState<"loading" | "questions" | "documents" | "failed">("loading");
  const [mode, setMode] = useState<"chat" | "form">("form");
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [held, setHeld] = useState<Record<string, DocumentAnswer>>({});
  const [busy, setBusy] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const [text, setText] = useState("");
  const [notice, setNotice] = useState("");

  const { health } = useHealth();
  useEffect(() => {
    if (health?.llm_available) setMode("chat");
  }, [health]);

  const begin = async () => {
    setStage("loading");
    try {
      const session = await api.createSession(lang);
      setSessionId(session.session_id);
      setQuestion(session.first_question ?? null);
      setStage(session.first_question ? "questions" : "documents");
    } catch {
      setStage("failed");
    }
  };

  useEffect(() => {
    void begin();
    // A new assessment starts each time this page opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toDocuments = async (id: string) => {
    const response = await api.checklist(id);
    setChecklist(response.documents);
    setStage("documents");
  };

  const answer = async (value: AnswerValue) => {
    if (!sessionId || !question) return;
    setBusy(true);
    setInvalid(false);
    try {
      const response = await api.answer(sessionId, question.field_id, value);
      setProfile(response.profile);
      setAnswered(response.progress.answered);
      setQuestion(response.next_question ?? null);
      if (!response.next_question) await toDocuments(sessionId);
    } catch {
      setInvalid(true);
    } finally {
      setBusy(false);
    }
  };

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    if (!sessionId || !text.trim()) return;
    setBusy(true);
    setNotice("");
    try {
      const response = await api.message(sessionId, text);
      setProfile(response.profile);
      setText("");
      const notes = response.extracted.flatMap((field) => (field.note ? [field.note] : []));
      const missed = response.extracted.length === 0 && !response.clarification;
      setNotice([response.clarification, ...notes, missed ? t("assess.nothing_found") : ""].filter(Boolean).join(" "));
      setQuestion(response.next_question ?? null);
      // Short replies like "yes" carry no field on their own, so follow-ups use the structured question.
      setMode("form");
      if (!response.next_question && !response.clarification) await toDocuments(sessionId);
    } catch {
      setNotice(t("assess.chat_unavailable"));
      setMode("form");
    } finally {
      setBusy(false);
    }
  };

  const finishDocuments = async () => {
    if (!sessionId) return;
    setBusy(true);
    try {
      await api.saveDocuments(sessionId, held);
      navigate("/confirm");
    } catch {
      setStage("failed");
    } finally {
      setBusy(false);
    }
  };

  const entries = Object.entries(profile);

  return (
    <section className="container-page py-8">
      <PageHead title="page.assess" lead="assess.lead" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          {stage === "loading" && <Loading />}
          {stage === "failed" && <ErrorNote onRetry={begin} />}

          {stage === "questions" && (
            <div className="panel flex flex-col gap-4">
              {notice && (
                <p role="status" className="text-sm">
                  {notice}
                </p>
              )}
              {mode === "form" && question && (
                <QuestionForm question={question} busy={busy} error={invalid} onAnswer={answer} />
              )}
              {mode === "chat" && (
                <form onSubmit={sendMessage} className="flex flex-col gap-3">
                  <label htmlFor="intake" className="font-medium">
                    {answered === 0 && Object.keys(profile).length === 0 ? t("assess.chat_label") : question?.question_text}
                  </label>
                  <textarea
                    id="intake"
                    className="input w-full"
                    rows={4}
                    value={text}
                    onChange={(event) => setText(event.target.value)}
                  />
                  <button type="submit" className="btn btn-primary self-start" disabled={busy || !text.trim()}>
                    {t("assess.chat_send")}
                  </button>
                </form>
              )}
              <button type="button" className="link-button self-start" onClick={() => setMode(mode === "form" ? "chat" : "form")}>
                {t(mode === "form" ? "assess.use_chat" : "assess.use_form")}
              </button>
            </div>
          )}

          {stage === "documents" && (
            <div className="panel flex flex-col gap-4">
              <h2 className="question">{t("documents.title")}</h2>
              <p className="text-sm text-muted">{t("documents.lead")}</p>
              <ul className="m-0 flex list-none flex-col gap-3 p-0">
                {checklist.map((item) => (
                  <li key={item.document_id} className="flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-3">
                    <div>
                      <p className="font-medium">{item.label}</p>
                      {item.issued_by_hint && <p className="text-sm text-muted">{item.issued_by_hint}</p>}
                    </div>
                    <div role="group" aria-label={item.label} className="cells">
                      {DOCUMENT_ANSWERS.map(({ value, label }) => (
                        <button
                          key={value}
                          type="button"
                          className="cell"
                          aria-pressed={held[item.document_id] === value}
                          onClick={() => setHeld({ ...held, [item.document_id]: value })}
                        >
                          {t(label)}
                        </button>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
              <button type="button" className="btn btn-primary self-start" disabled={busy} onClick={finishDocuments}>
                {t("answer.continue")}
              </button>
            </div>
          )}
        </div>

        <aside className="panel self-start" aria-label={t("assess.sidebar")}>
          <h2 className="row-title">{t("assess.sidebar")}</h2>
          <p className="mt-1 text-sm text-muted">{t("assess.progress", { n: answered })}</p>
          {entries.length > 0 && (
            <dl className="mt-3 flex flex-col gap-2 text-sm">
              {entries.map(([field, entry]) => (
                <div key={field} className="flex justify-between gap-3 border-b border-rule pb-1">
                  <dt className="text-muted">{entry.label}</dt>
                  <dd className="m-0 text-right font-medium">{entry.display}</dd>
                </div>
              ))}
            </dl>
          )}
        </aside>
      </div>
    </section>
  );
}
