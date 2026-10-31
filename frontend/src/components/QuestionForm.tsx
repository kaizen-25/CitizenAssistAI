import { useEffect, useState, type FormEvent } from "react";
import type { AnswerValue, Question } from "../api/client";
import { useT } from "../hooks/useT";

const DECLINED = "__declined__";

interface Props {
  question: Question;
  busy?: boolean;
  error?: boolean;
  onAnswer: (value: AnswerValue) => void;
}

export function QuestionForm({ question, busy, error, onAnswer }: Props) {
  const { t } = useT();
  const [text, setText] = useState("");
  useEffect(() => setText(""), [question.field_id]);

  const numeric = question.answer_type === "number" || question.answer_type === "integer";
  const choices =
    question.answer_type === "boolean"
      ? [
          { value: true as AnswerValue, label: t("answer.yes") },
          { value: false as AnswerValue, label: t("answer.no") },
          ...question.options,
        ]
      : question.options;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (text.trim() !== "") onAnswer(Number(text));
  };

  return (
    <div className="flex flex-col gap-3">
      <h2 className="question" id={`q-${question.field_id}`}>
        {question.question_text}
      </h2>
      {question.schemes_affected > 0 && <p className="text-sm text-muted">{question.reason}</p>}

      {numeric && (
        <form onSubmit={submit} className="flex flex-wrap items-stretch gap-2">
          <input
            className="input"
            type="number"
            inputMode="numeric"
            min={0}
            step={question.answer_type === "integer" ? 1 : "any"}
            value={text}
            onChange={(event) => setText(event.target.value)}
            aria-labelledby={`q-${question.field_id}`}
            autoFocus
          />
          <button type="submit" className="btn btn-primary" disabled={busy || text.trim() === ""}>
            {t("answer.continue")}
          </button>
        </form>
      )}

      {choices.length > 0 && (
        <div role="group" aria-labelledby={`q-${question.field_id}`} className="flex flex-wrap gap-2">
          {choices.map((option) => (
            <button
              key={String(option.value)}
              type="button"
              disabled={busy}
              className={option.value === DECLINED ? "btn btn-quiet" : "btn"}
              onClick={() => onAnswer(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-ineligible">
          {t("answer.invalid")}
        </p>
      )}
    </div>
  );
}
