import { useT, type StringKey } from "../hooks/useT";

export function Placeholder({ title }: { title: StringKey }) {
  const { t } = useT();

  return (
    <section className="container-page py-12">
      <h1 className="text-(length:--text-section)">{t(title)}</h1>
      <p className="mt-4 text-muted">{t("page.placeholder")}</p>
    </section>
  );
}
