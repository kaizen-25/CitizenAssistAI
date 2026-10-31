import { CircleCheck, CircleHelp, CircleMinus, CircleX, ClipboardCheck, type LucideIcon } from "lucide-react";
import type { RuleResult, SchemeStatus } from "../api/client";
import { useT, type StringKey } from "../hooks/useT";

type Tone = "eligible" | "unknown" | "ineligible" | "neutral";

const STATUS: Record<SchemeStatus, { icon: LucideIcon; tone: Tone; label: StringKey }> = {
  potentially_eligible: { icon: CircleCheck, tone: "eligible", label: "status.potentially_eligible" },
  cannot_determine: { icon: CircleHelp, tone: "unknown", label: "status.cannot_determine" },
  not_eligible: { icon: CircleX, tone: "ineligible", label: "status.not_eligible" },
};

const OUTCOME: Record<RuleResult["outcome"], { icon: LucideIcon; tone: Tone; label: StringKey }> = {
  PASS: { icon: CircleCheck, tone: "eligible", label: "outcome.PASS" },
  FAIL: { icon: CircleX, tone: "ineligible", label: "outcome.FAIL" },
  UNKNOWN: { icon: CircleHelp, tone: "unknown", label: "outcome.UNKNOWN" },
  MANUAL: { icon: ClipboardCheck, tone: "neutral", label: "outcome.MANUAL" },
  NOT_APPLICABLE: { icon: CircleMinus, tone: "neutral", label: "outcome.NOT_APPLICABLE" },
};

function Chip({ icon: Icon, tone, label }: { icon: LucideIcon; tone: Tone; label: StringKey }) {
  const { t } = useT();
  return (
    <span className={`chip chip-${tone}`}>
      <Icon size={16} aria-hidden="true" />
      {t(label)}
    </span>
  );
}

export function StatusChip({ status }: { status: SchemeStatus }) {
  return <Chip {...STATUS[status]} />;
}

export function OutcomeChip({ outcome }: { outcome: RuleResult["outcome"] }) {
  return <Chip {...OUTCOME[outcome]} />;
}
