import { useState, type FormEvent } from "react";
import { api, type ChatResponse } from "../api/client";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";

export function AskPanel() {
  const { t, lang } = useT();
  const { sessionId } = useSession();
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFailed(false);
    try {
      setResponse(await api.chat(question, lang, sessionId));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="ask" className="panel no-print mt-6 flex flex-col gap-3">
      <h2 id="ask" className="row-title">{t("ask.title")}</h2>
      <form onSubmit={ask} className="flex flex-wrap gap-2">
        <input
          className="input min-w-0 flex-1 basis-64"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          aria-labelledby="ask"
        />
        <button type="submit" className="btn" disabled={busy || !question.trim()}>
          {t("ask.send")}
        </button>
      </form>

      {busy && <p role="status" className="text-sm text-muted">{t("ask.thinking")}</p>}
      {failed && <p role="alert" className="text-sm text-ineligible">{t("ask.failed")}</p>}

      {response && !busy && (
        <div role="status" className="flex flex-col gap-2">
          <p className="whitespace-pre-line">{response.answer.replace(/\s*\[[\w.-]+\]/g, "")}</p>
          {(response.citations ?? []).length > 0 && (
            <ul className="m-0 flex list-none flex-col gap-1 p-0 text-sm">
              {[...new Map((response.citations ?? []).map((c) => [c.source_url, c])).values()].map((citation) => (
                <li key={citation.source_url}>
                  <a href={citation.source_url} target="_blank" rel="noreferrer">{citation.source_title}</a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
