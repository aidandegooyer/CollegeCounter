import { MATCH_RESULT_STYLES, type MatchResult } from "@/services/matchResult";

export function MatchResultBadge({
  result,
  className = "",
}: {
  result: MatchResult;
  className?: string;
}) {
  const { label, badge } = MATCH_RESULT_STYLES[result];
  return (
    <span
      className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded font-mono text-xs font-bold ${badge} ${className}`}
    >
      {label}
    </span>
  );
}
