import { Link } from "react-router-dom";
import { useT } from "../hooks/useT";

export function Landing() {
  const { t } = useT();

  return (
    <section className="container-page flex flex-col items-start gap-6 py-16 md:py-24">
      <h1>{t("landing.title")}</h1>
      <p className="max-w-xl text-(length:--text-lead)">{t("landing.lead")}</p>
      <Link to="/assess" className="btn btn-primary">
        {t("landing.action")}
      </Link>
    </section>
  );
}
