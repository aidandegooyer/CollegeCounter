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
      className={`inline-block w-6 rounded text-center text-xs font-bold ${badge} ${className}`}
    >
      {label}
    </span>
  );
}
