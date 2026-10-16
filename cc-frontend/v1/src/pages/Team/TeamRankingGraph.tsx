import { useEffect, useId, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { format, isValid } from "date-fns";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import type { PublicTeamRankingHistoryItem } from "@/services/api";
import {
  useCurrentSeason,
  usePublicSeasons,
  useTeamRankingHistory,
} from "@/services/hooks";

interface TeamRankingGraphProps {
  teamId: string;
}

export default function TeamRankingGraph({ teamId }: TeamRankingGraphProps) {
  const seasonsQuery = usePublicSeasons({
    sort: "start_date",
    order: "desc",
    page_size: 100,
  });
  const currentSeasonQuery = useCurrentSeason();
  const seasons = seasonsQuery.data?.results ?? [];
  const seasonsLoading = seasonsQuery.isLoading || currentSeasonQuery.isLoading;

  // Default to the current season until the user picks one. Wait for the
  // current-season lookup so we don't briefly fetch a different season first.
  const [pickedSeasonId, setPickedSeasonId] = useState<string>();
  const seasonId = seasonsLoading
    ? undefined
    : (pickedSeasonId ?? currentSeasonQuery.data?.id ?? seasons[0]?.id);

  const history = useTeamRankingHistory(teamId, seasonId);
  const { data } = history;
  const isLoading = seasonsLoading || history.isLoading;
  // A failed season lookup is reported rather than silently falling back to
  // another season, unless the user has already picked one themselves.
  const seasonsError =
    seasonsQuery.error ?? (pickedSeasonId ? null : currentSeasonQuery.error);

  // API returns newest first; the chart reads left to right in time.
  // Snapshots with an unparseable date are dropped so they can't break the chart.
  const points = useMemo(
    () =>
      (data?.ranking_history ?? [])
        .filter((p) => isValid(new Date(p.ranking_date)))
        .sort(
          (a, b) =>
            new Date(a.ranking_date).getTime() -
            new Date(b.ranking_date).getTime(),
        ),
    [data],
  );
  // Keep showing loaded data if only a background refresh failed
  const error = seasonsError ?? (points.length === 0 ? history.error : null);

  function renderBody() {
    if (isLoading) {
      return (
        <div className="flex h-32 items-center justify-center">
          <Spinner />
        </div>
      );
    }
    if (error) {
      return (
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            There was an error loading the ranking history. Please try again
            later.
          </AlertDescription>
        </Alert>
      );
    }
    if (points.length === 0) {
      return (
        <div className="text-muted-foreground rounded-xl border-2 border-dashed py-10 text-center">
          {seasonId
            ? "No ranking history for this season"
            : "No seasons available"}
        </div>
      );
    }
    return <CollapsibleRankHistory points={points} />;
  }

  return (
    <section className="mx-4 mt-8">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-2xl">Ranking History</h2>
        {seasons.length > 0 && seasonId && (
          <Select value={seasonId} onValueChange={setPickedSeasonId}>
            <SelectTrigger className="w-48" aria-label="Season">
              <SelectValue placeholder="Select season" />
            </SelectTrigger>
            <SelectContent>
              {seasons.map((season) => (
                <SelectItem key={season.id} value={season.id}>
                  {season.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      {renderBody()}
    </section>
  );
}

// Collapsed by default: shows the season's peak rank and when it was first
// reached; expanding reveals the full graph.
function CollapsibleRankHistory({
  points,
}: {
  points: PublicTeamRankingHistoryItem[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const chartId = useId();

  // Points are oldest first, so the first match is when the peak was reached
  const peak = points.reduce((best, p) => (p.rank < best.rank ? p : best));

  return (
    <div className="bg-background rounded-xl border">
      <button
        type="button"
        className="group flex w-full cursor-pointer items-center justify-between gap-4 rounded-xl px-4 py-3 text-left"
        aria-expanded={isOpen}
        aria-controls={chartId}
        onClick={() => setIsOpen((open) => !open)}
      >
        <div>
          <div className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Peak Rank
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-semibold">#{peak.rank}</span>
            <span className="text-muted-foreground text-sm">
              {formatRankingDate(peak.ranking_date, "MMM d, yyyy")}
            </span>
          </div>
        </div>
        {/* Plain text toggle: no border or fill */}
        <span className="flex h-9 items-center gap-2 rounded-md px-3 text-sm whitespace-nowrap">
          {isOpen ? "Hide graph" : "Show graph"}
          <ChevronDown
            className={`size-4 opacity-50 transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </span>
      </button>
      {isOpen && (
        <div id={chartId} className="border-t p-2">
          <RankLineChart points={points} />
        </div>
      )}
    </div>
  );
}

const HEIGHT = 240;
const TOOLTIP_GAP = 10;
const MARGIN = { top: 16, right: 48, bottom: 36, left: 44 };

// Smallest of 1, 2, 5, 10, 20, 50... that splits `range` into about `count` steps
function niceStep(range: number, count: number) {
  const raw = Math.max(range / count, 1);
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].find((m) => m * magnitude >= raw) ?? 10;
  return step * magnitude;
}

// Up to `count` evenly spaced indices, always including the first and last
function spacedIndices(length: number, count: number) {
  if (length <= count) return Array.from({ length }, (_, i) => i);
  return Array.from({ length: count }, (_, i) =>
    Math.round((i * (length - 1)) / (count - 1)),
  );
}

function formatRankingDate(date: string, pattern = "MMM d") {
  const parsed = new Date(date);
  return isValid(parsed) ? format(parsed, pattern) : "Unknown date";
}

// Single-series line chart of rank over time. The y-axis is inverted so #1
// sits at the top; hover or arrow keys move a crosshair across the snapshots.
function RankLineChart({ points }: { points: PublicTeamRankingHistoryItem[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(entry.contentRect.width),
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 0);
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;

  const times = points.map((p) => new Date(p.ranking_date).getTime());
  const minTime = times[0];
  const maxTime = times[times.length - 1];
  const x = (i: number) =>
    MARGIN.left +
    (maxTime === minTime
      ? plotWidth / 2
      : ((times[i] - minTime) / (maxTime - minTime)) * plotWidth);

  const ranks = points.map((p) => p.rank);
  const minRank = Math.min(...ranks);
  const maxRank = Math.max(...ranks);
  const pad = Math.max(1, Math.ceil((maxRank - minRank) * 0.1));
  const yLow = Math.max(1, minRank - pad);
  const yHigh = maxRank + pad;
  const y = (rank: number) =>
    MARGIN.top + ((rank - yLow) / (yHigh - yLow)) * plotHeight;

  const step = niceStep(yHigh - yLow, 5);
  const yTicks: number[] = [];
  for (let t = Math.ceil(yLow / step) * step; t <= yHigh; t += step) {
    if (t >= 1) yTicks.push(t);
  }
  const xTickIndices = spacedIndices(points.length, width < 480 ? 3 : 5);

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p.rank)}`)
    .join(" ");

  const nearestIndex = (clientX: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return null;
    const px = clientX - rect.left;
    let best = 0;
    for (let i = 1; i < points.length; i++) {
      if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i;
    }
    return best;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const last = points.length - 1;
    const current = activeIndex ?? last;
    if (e.key === "ArrowLeft") setActiveIndex(Math.max(current - 1, 0));
    else if (e.key === "ArrowRight")
      setActiveIndex(Math.min(current + 1, last));
    else if (e.key === "Home") setActiveIndex(0);
    else if (e.key === "End") setActiveIndex(last);
    else if (e.key === "Escape") setActiveIndex(null);
    else return;
    e.preventDefault();
  };

  const first = points[0];
  const latest = points[points.length - 1];
  const summary = `Rank over the season, from #${first.rank} on ${formatRankingDate(
    first.ranking_date,
    "MMM d, yyyy",
  )} to #${latest.rank} on ${formatRankingDate(latest.ranking_date, "MMM d, yyyy")}. Best rank #${minRank}.`;

  const active = activeIndex !== null ? points[activeIndex] : null;
  const tooltipLeft =
    activeIndex !== null
      ? Math.min(Math.max(x(activeIndex), 70), Math.max(width - 70, 70))
      : 0;
  // Tooltip sits just above the active point. Near the top of the chart it
  // overlaps the card header, which is fine since it floats above everything.
  const tooltipTop = active ? y(active.rank) - TOOLTIP_GAP : 0;

  return (
    <div>
      <div
        ref={containerRef}
        className="focus-visible:ring-ring relative rounded-md outline-none focus-visible:ring-2"
        tabIndex={0}
        role="img"
        aria-label={`${summary} Use the arrow keys to step through snapshots.`}
        onKeyDown={handleKeyDown}
        onBlur={() => setActiveIndex(null)}
        onPointerMove={(e) => setActiveIndex(nearestIndex(e.clientX))}
        onPointerLeave={() => setActiveIndex(null)}
      >
        {width > 0 && (
          <svg width={width} height={HEIGHT} aria-hidden="true">
            {/* Gridlines and rank labels */}
            {yTicks.map((tick) => (
              <g key={tick}>
                <line
                  x1={MARGIN.left}
                  x2={MARGIN.left + plotWidth}
                  y1={y(tick)}
                  y2={y(tick)}
                  className="stroke-border"
                  strokeWidth={1}
                />
                <text
                  x={MARGIN.left - 8}
                  y={y(tick)}
                  textAnchor="end"
                  dominantBaseline="middle"
                  className="fill-muted-foreground text-xs"
                >
                  #{tick}
                </text>
              </g>
            ))}

            {/* Date labels */}
            {xTickIndices.map((i) => (
              <text
                key={points[i].id}
                x={x(i)}
                y={HEIGHT - 8}
                textAnchor="middle"
                className="fill-muted-foreground text-xs"
              >
                {formatRankingDate(points[i].ranking_date)}
              </text>
            ))}

            {/* Crosshair */}
            {activeIndex !== null && (
              <line
                x1={x(activeIndex)}
                x2={x(activeIndex)}
                y1={MARGIN.top}
                y2={MARGIN.top + plotHeight}
                className="stroke-muted-foreground"
                strokeWidth={1}
              />
            )}

            <path
              d={linePath}
              fill="none"
              className="stroke-chart-1 dark:stroke-primary"
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />

            {points.map((p, i) => (
              <circle
                key={p.id}
                cx={x(i)}
                cy={y(p.rank)}
                r={i === activeIndex ? 5 : 4}
                className="fill-chart-1 stroke-background dark:fill-primary"
                strokeWidth={2}
              />
            ))}

            {/* Direct label on the latest snapshot only */}
            <text
              x={x(points.length - 1) + 10}
              y={y(latest.rank)}
              dominantBaseline="middle"
              className="fill-foreground text-sm font-semibold"
            >
              #{latest.rank}
            </text>
          </svg>
        )}

        {active && (
          <div
            className="bg-popover text-popover-foreground pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border px-3 py-2 text-xs whitespace-nowrap shadow-md"
            style={{ left: tooltipLeft, top: tooltipTop }}
          >
            <div className="text-muted-foreground">
              {formatRankingDate(active.ranking_date, "MMM d, yyyy")}
            </div>
            <div className="text-sm font-semibold">#{active.rank}</div>
            <div className="text-muted-foreground">
              ELO {Math.round(active.elo)}
            </div>
          </div>
        )}
      </div>

      {/* Table view for screen readers. sr-only goes on a wrapper because a
          table's caption renders outside the table box and would leak out. */}
      <div className="sr-only">
        <table>
          <caption>Ranking history</caption>
          <thead>
            <tr>
              <th>Date</th>
              <th>Rank</th>
              <th>ELO</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.id}>
                <td>{formatRankingDate(p.ranking_date, "MMM d, yyyy")}</td>
                <td>#{p.rank}</td>
                <td>{Math.round(p.elo)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
