import type { UnlockReport } from "../api/client";
import { useT } from "../hooks/useT";

interface Props {
  report: UnlockReport;
  docLabel: (id: string) => string;
}

export function UnlockPlan({ report, docLabel }: Props) {
  const { t } = useT();

  return (
    <ol className="route">
      {(report.plan ?? []).map((step) => {
        const n = step.newly_ready.length;
        const doc = docLabel(step.document_id);
        return (
          <li key={step.step} className="plate">
            <span className="plate-step" aria-hidden="true">
              {step.step}
            </span>
            <div className="flex min-w-0 flex-col gap-1">
              <h3 className="plate-title">{doc}</h3>
              <p>
                {n === 0
                  ? t("unlock.progress", { doc })
                  : t(n === 1 ? "unlock.sentence_one" : "unlock.sentence", { doc, n })}
              </p>
              <p className="plate-count">{t("unlock.cumulative", { n: step.cumulative_ready })}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
