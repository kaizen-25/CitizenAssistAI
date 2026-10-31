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
      <section className="container-page grid items-center gap-8 py-12 md:py-20 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="flex flex-col items-start gap-6">
          <h1>{t("landing.title")}</h1>
          <p className="max-w-xl text-(length:--text-lead)">{t("landing.lead")}</p>
          <Link to="/assess" className="btn btn-primary">
            {t("landing.action")}
          </Link>
        </div>

        <figure className="sign m-0">
          <figcaption className="sign-caption">{t("landing.sign_caption")}</figcaption>
          <p className="sign-step"><span aria-hidden="true">1</span>{t("landing.sign_first")}</p>
          <p className="sign-step"><span aria-hidden="true">2</span>{t("landing.sign_next")}</p>
        </figure>
      </section>

      <section className="bg-paper-2">
        <div className="container-page py-10">
          <ol className="route m-0">
            {STEPS.map((step, index) => (
              <li key={step.title} className="plate">
                <span className="plate-step" aria-hidden="true">{index + 1}</span>
                <div className="flex flex-col gap-1">
                  <h2 className="plate-title">{t(step.title)}</h2>
                  <p>{t(step.body)}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </>
  );
}
