interface RankChangeProps {
  // Places moved since the previous ranking: positive is up, negative down
  change: number;
  className?: string;
  iconClassName?: string;
}

function RankChange({
  change,
  className = "text-lg",
  iconClassName = "h-4 w-4",
}: RankChangeProps) {
  return (
    <span
      className={
        `flex items-center font-mono ${className} ` +
        (change > 0
          ? "text-green-500"
          : change < 0
            ? "text-red-500"
            : "text-muted-foreground")
      }
    >
      {change !== 0 && (
        <svg
          className={`mr-1 inline-block ${iconClassName}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d={change > 0 ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"}
          />
        </svg>
      )}
      {change === 0 ? "-" : Math.abs(change)}
    </span>
  );
}

export default RankChange;
