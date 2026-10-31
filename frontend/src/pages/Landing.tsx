import { Link } from "react-router-dom";
import { useT, type StringKey } from "../hooks/useT";

const STEPS: { title: StringKey; body: StringKey }[] = [
  { title: "landing.step1", body: "landing.step1_body" },
  { title: "landing.step2", body: "landing.step2_body" },
  { title: "landing.step3", body: "landing.step3_body" },
];

export function Landing() {
  const { t } = useT();

  return (
    <>
      <section className="container-page grid items-center gap-10 py-12 md:py-16 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="flex flex-col items-start gap-6">
          <h1 className="hero-title">{t("landing.title")}</h1>
          <p className="max-w-xl text-(length:--text-lead) text-ink-2">{t("landing.lead")}</p>
          <Link to="/assess" className="btn btn-primary">
            {t("landing.action")}
          </Link>
        </div>

        <figure className="slip m-0">
          <figcaption className="slip-caption">{t("landing.sign_caption")}</figcaption>
          <ol className="route">
            <li className="plate">
              <span className="plate-step" aria-hidden="true">1</span>
              <p className="plate-title self-center font-(family-name:--font-display) font-semibold">{t("landing.sign_first")}</p>
            </li>
            <li className="plate">
              <span className="plate-step" aria-hidden="true">2</span>
              <p className="plate-title self-center font-(family-name:--font-display) font-semibold">{t("landing.sign_next")}</p>
            </li>
          </ol>
        </figure>
      </section>

      <section className="container-page pb-16">
        <ol className="steps">
          {STEPS.map((step, index) => (
            <li key={step.title} className="step">
              <span className="step-number" aria-hidden="true">{index + 1}</span>
              <h2 className="step-title">{t(step.title)}</h2>
              <p className="text-ink-2">{t(step.body)}</p>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
