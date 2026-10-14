import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchSyncStatus,
  type SyncStatus,
  type SyncTier,
} from "@/services/api";
import { formatDistanceToNow } from "date-fns";
import { useEffect, useState } from "react";
import { Link } from "react-router";

const REFRESH_MS = 30_000;

const TIER_LABELS: Record<SyncTier, string> = {
  live: "Live",
  overdue: "Overdue (should have started)",
  imminent: "Starting within the hour",
  today: "Starting today",
  upcoming: "This week",
  straggler: "Unfinished, 12h+ past start",
};

const PLATFORM_LABELS: Record<string, string> = {
  faceit: "Faceit",
  leaguespot: "LeagueSpot",
  regentsleague: "Regents League",
};

function ago(date: string | null) {
  return date
    ? formatDistanceToNow(new Date(date), { addSuffix: true })
    : "never";
}

function Stat({
  label,
  value,
  warn = false,
}: {
  label: string;
  value: string | number;
  warn?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border-2 p-4 py-3 ${warn ? "border-red-500" : ""}`}
    >
      <div className="text-muted-foreground text-sm">{label}</div>
      <div className={`text-2xl font-semibold ${warn ? "text-red-500" : ""}`}>
        {value}
      </div>
    </div>
  );
}

// How the background match sync is doing; refreshes itself every 30s
function SyncMetrics() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState("");

  const load = () => {
    fetchSyncStatus()
      .then((data) => {
        setStatus(data);
        setError("");
      })
      .catch((err) => {
        console.error("Failed to load sync status:", err);
        setError(
          err?.response?.data?.error || "Failed to load match sync status.",
        );
      });
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, []);

  if (error && !status) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertDescription className="flex flex-col items-start gap-2">
          {error}
          <Button variant="outline" size="sm" onClick={load}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!status) {
    return (
      <div className="mt-4 flex justify-center">
        <Spinner />
      </div>
    );
  }

  const dueNow = Object.values(status.tiers).reduce(
    (total, tier) => total + tier.due,
    0,
  );
  const minutesLate = Math.round(status.most_late_seconds / 60);

  return (
    <div className="mt-4 space-y-6">
      {status.worker_behind && (
        <Alert variant="destructive">
          <AlertDescription>
            Matches are waiting up to {minutesLate} min past when they should
            have been refreshed. The match-sync worker may not be running, or it
            can't keep up.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Last refresh" value={ago(status.last_synced_at)} />
        <Stat
          label="Worker"
          value={status.worker_behind ? `${minutesLate} min behind` : "On time"}
          warn={status.worker_behind}
        />
        <Stat label="Due now" value={dueNow} />
        <Stat
          label="Failing (retrying)"
          value={status.failing}
          warn={status.failing > 0}
        />
        <Stat label="Stopped (needs review)" value={status.disabled} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 font-semibold">By platform</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Platform</TableHead>
                <TableHead className="text-right">Tracked</TableHead>
                <TableHead className="text-right">Due</TableHead>
                <TableHead className="text-right">Failing</TableHead>
                <TableHead>Last refresh</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(status.platforms).map(([platform, stats]) => (
                <TableRow key={platform}>
                  <TableCell>{PLATFORM_LABELS[platform] ?? platform}</TableCell>
                  <TableCell className="text-right">{stats.tracked}</TableCell>
                  <TableCell className="text-right">{stats.due}</TableCell>
                  <TableCell
                    className={`text-right ${stats.failing ? "text-red-500" : ""}`}
                  >
                    {stats.failing}
                  </TableCell>
                  <TableCell>{ago(stats.last_synced_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <div>
          <h3 className="mb-2 font-semibold">By tier</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tier</TableHead>
                <TableHead className="text-right">Tracked</TableHead>
                <TableHead className="text-right">Due</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(Object.keys(TIER_LABELS) as SyncTier[]).map((tier) => (
                <TableRow key={tier}>
                  <TableCell>{TIER_LABELS[tier]}</TableCell>
                  <TableCell className="text-right">
                    {status.tiers[tier].tracked}
                  </TableCell>
                  <TableCell className="text-right">
                    {status.tiers[tier].due}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      <div>
        <h3 className="mb-2 font-semibold">Recent errors</h3>
        {status.recent_errors.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No matches are failing to refresh.
          </p>
        ) : (
          <ul className="space-y-2">
            {status.recent_errors.map((row) => (
              <li key={row.match_id} className="rounded-xl border-2 p-3 py-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Link
                    to={`/matches/${row.match_id}`}
                    className="font-semibold hover:underline"
                  >
                    {row.team1} vs {row.team2}
                  </Link>
                  <div className="flex items-center gap-2 text-sm">
                    <Badge variant="outline">
                      {PLATFORM_LABELS[row.platform] ?? row.platform}
                    </Badge>
                    <span className="text-muted-foreground">
                      {row.failures} in a row · {ago(row.at)}
                    </span>
                  </div>
                </div>
                <div className="text-muted-foreground mt-1 break-all font-mono text-xs">
                  {row.error}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default SyncMetrics;
