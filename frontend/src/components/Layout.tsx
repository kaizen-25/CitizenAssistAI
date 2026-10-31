import { Link, Outlet } from "react-router-dom";
import { useHealth } from "../hooks/useHealth";
import { useT, type Language } from "../hooks/useT";

const LANGUAGES: { code: Language; name: string }[] = [
  { code: "en", name: "English" },
  { code: "hi", name: "हिन्दी" },
  { code: "pa", name: "ਪੰਜਾਬੀ" },
];

export function Layout() {
  const { t, lang, setLang } = useT();
  const { health, failed } = useHealth();

  return (
    <div className="flex min-h-dvh flex-col">
      {health?.show_unverified && (
        <p role="alert" className="bg-ineligible px-4 py-2 text-center font-medium text-accent-ink">
          {t("banner.unverified")}
        </p>
      )}

      <header className="border-b-2 border-ink bg-paper-3">
        <div className="container-page flex flex-wrap items-center justify-between gap-3 py-3">
          <Link to="/" className="text-xl font-extrabold no-underline">
            {t("app.name")}
          </Link>
          <div role="group" aria-label={t("language.label")} className="flex divide-x-2 divide-ink border-2 border-ink">
            {LANGUAGES.map(({ code, name }) => (
              <button key={code} type="button" className="cell" aria-pressed={lang === code} onClick={() => setLang(code)}>
                {name}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-ink text-paper">
        <div className="container-page flex flex-col gap-2 py-6 text-sm">
          <p className="max-w-3xl">{t("disclaimer")}</p>
          {(health || failed) && (
            <p className="text-rule">
              {health ? t("health.ok", { n: health.schemes_loaded }) : t("health.down")}
            </p>
          )}
        </div>
      </footer>
    </div>
  );
}
