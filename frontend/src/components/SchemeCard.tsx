import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type AnswerValue, type Question, type ResultsResponse, type SchemeResult } from "../api/client";
import { useSession } from "../hooks/useSession";
import { useT } from "../hooks/useT";
import { QuestionForm } from "./QuestionForm";
import { SchemeLinks } from "./SchemeLinks";
import { StatusChip } from "./StatusChip";

interface Props {
  result: SchemeResult;
  labels: ResultsResponse["labels"];
  onChanged: () => void;
}

export function matchedCriteria(result: SchemeResult) {
  const checked = result.rules.filter((rule) => ["PASS", "FAIL", "UNKNOWN"].includes(rule.outcome));
  return { matched: checked.filter((rule) => rule.outcome === "PASS").length, total: checked.length };
}

export function SchemeCard({ result, labels, onChanged }: Props) {
  const { t } = useT();
  const { sessionId } = useSession();
  const [question, setQuestion] = useState<Question | null>(null);
  const [failed, setFailed] = useState(false);
  const { matched, total } = matchedCriteria(result);
  const blockers = [...result.documents.missing, ...result.documents.unsure];

  const openQuestion = async (fieldId: string) => {
    if (sessionId) setQuestion(await api.question(sessionId, fieldId));
  };

  const answer = async (value: AnswerValue) => {
    if (!sessionId || !question) return;
    try {
      await api.answer(sessionId, question.field_id, value);
      setQuestion(null);
      onChanged();
    } catch {
      setFailed(true);
    }
  };

  return (
    <article className="row flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="row-title">
            <Link to={`/scheme/${result.scheme_id}`}>{result.name}</Link>
          </h2>
          <p className="text-sm text-muted">{result.department}</p>
        </div>
        <StatusChip status={result.status} />
      </div>

      <p className="text-sm">{t("results.matched", { matched, total })}</p>

      {result.unknown_fields.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span>{t("results.still_need")}</span>
          {result.unknown_fields.map((field) => (
            <button key={field} type="button" className="btn btn-small" onClick={() => openQuestion(field)}>
              {t("results.answer_now", { field: labels.fields?.[field] ?? field })}
            </button>
          ))}
        </div>
      )}

      {question && <QuestionForm question={question} error={failed} onAnswer={answer} />}

      {blockers.length > 0 && (
        <p className="text-sm">
          {t("results.missing_docs", { docs: blockers.map((id) => labels.documents?.[id] ?? id).join(", ") })}
        </p>
      )}

      <SchemeLinks source={result.source} applicationUrl={result.application_url ?? null} />
    </article>
  );
}
