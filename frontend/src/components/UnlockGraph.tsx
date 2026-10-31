import type { SchemeResult, UnlockReport } from "../api/client";
import { useT } from "../hooks/useT";

const ROW = 56;
const WIDTH = 720;
const LEFT = 200;
const RIGHT = 340;
const BEND = (LEFT + RIGHT) / 2;

interface Props {
  report: UnlockReport;
  schemes: SchemeResult[];
}

function shorten(text: string, limit: number) {
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

export function UnlockGraph({ report, schemes }: Props) {
  const { t } = useT();
  const ranking = report.ranking ?? [];
  const schemeIds = [...new Set(ranking.flatMap((entry) => entry.required_by))];
  const name = (id: string) => schemes.find((scheme) => scheme.scheme_id === id)?.name ?? id;
  const y = (index: number) => index * ROW + ROW / 2;
  const height = Math.max(ranking.length, schemeIds.length) * ROW;

  return (
    <figure className="m-0 overflow-x-auto">
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="graph" role="img" aria-label={t("unlock.graph_label")}>
        {ranking.flatMap((entry, docIndex) =>
          entry.required_by.map((id) => (
            <path
              key={`${entry.document_id}-${id}`}
              d={`M ${LEFT} ${y(docIndex)} C ${BEND} ${y(docIndex)}, ${BEND} ${y(schemeIds.indexOf(id))}, ${RIGHT} ${y(schemeIds.indexOf(id))}`}
              className="graph-edge"
            />
          )),
        )}
        {ranking.map((entry, index) => (
          <g key={entry.document_id}>
            <rect x={0} y={y(index) - 22} width={LEFT} height={44} className="graph-doc" />
            <text x={12} y={y(index) + 5} className="graph-doc-text">
              {shorten(entry.label, 26)}
            </text>
          </g>
        ))}
        {schemeIds.map((id, index) => (
          <g key={id}>
            <rect x={RIGHT} y={y(index) - 22} width={WIDTH - RIGHT} height={44} className="graph-scheme" />
            <text x={RIGHT + 12} y={y(index) + 5} className="graph-scheme-text">
              {shorten(name(id), 46)}
            </text>
          </g>
        ))}
      </svg>
    </figure>
  );
}
