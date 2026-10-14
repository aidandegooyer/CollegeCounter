import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import {
  fetchSyncReview,
  retryMatchSync,
  updateMatch,
  type SyncReviewMatch,
} from "@/services/api";
import { formatDistanceToNow } from "date-fns";
import { useEffect, useState } from "react";
import { Link } from "react-router";

// The backend's error message from a failed API call, if it sent one
function apiErrorMessage(err: unknown, fallback: string) {
  const response = (err as { response?: { data?: { error?: string } } })
    .response;
  return response?.data?.error || fallback;
}

// Matches the background sync has given up on (failing, or unfinished long
// after their date) or that are in a platform state we don't map yet
function SyncReview() {
  const [matches, setMatches] = useState<SyncReviewMatch[] | null>(null);
  const [loadError, setLoadError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = () => {
    setLoadError("");
    fetchSyncReview()
      .then(setMatches)
      .catch((err) => {
        console.error("Failed to load matches needing review:", err);
        setLoadError(
          apiErrorMessage(err, "Failed to load matches needing review."),
        );
      });
  };
  useEffect(load, []);

  const note = (id: string, text: string) =>
    setNotes((prev) => ({ ...prev, [id]: text }));

  const retry = async (match: SyncReviewMatch) => {
    setBusyId(match.id);
    try {
      const result = await retryMatchSync(match.id);
      if (result.outcome === "failed") {
        note(match.id, `Still failing: ${result.error}`);
      } else if (result.still_stale) {
        note(
          match.id,
          `Refreshed (${result.status}), but it's still unfinished long after its date, so it will be flagged again. Edit or cancel it instead.`,
        );
      } else {
        note(match.id, `Refreshed (${result.status}); syncing again.`);
      }
      load();
    } catch (err) {
      console.error("Retry failed:", err);
      note(match.id, apiErrorMessage(err, "Retry failed."));
    } finally {
      setBusyId(null);
    }
  };

  const cancel = async (match: SyncReviewMatch) => {
    if (
      !window.confirm(`Mark ${match.team1} vs ${match.team2} as cancelled?`)
    ) {
      return;
    }
    setBusyId(match.id);
    try {
      await updateMatch(match.id, { status: "cancelled" });
      load();
    } catch (err) {
      console.error("Cancel failed:", err);
      note(match.id, apiErrorMessage(err, "Couldn't cancel the match."));
    } finally {
      setBusyId(null);
    }
  };

  if (loadError) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertDescription className="flex flex-col items-start gap-2">
          {loadError}
          <Button variant="outline" size="sm" onClick={load}>
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!matches) {
    return (
      <div className="mt-4 flex justify-center">
        <Spinner />
      </div>
    );
  }

  if (matches.length === 0) {
    return (
      <p className="text-muted-foreground mt-4">
        No matches need review. Matches update automatically.
      </p>
    );
  }

  return (
    <ul className="mt-4 space-y-3">
      {matches.map((match) => (
        <li key={match.id} className="rounded-xl border-2 p-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <Link
                to={`/matches/${match.id}`}
                className="font-semibold hover:underline"
              >
                {match.team1} vs {match.team2}
              </Link>
              <div className="text-muted-foreground text-sm">
                {match.competition ?? "No competition"} · {match.platform} ·{" "}
                {formatDistanceToNow(new Date(match.date), { addSuffix: true })}
              </div>
              <div className="mt-1 text-sm">
                {match.sync_disabled
                  ? match.sync_failures > 0
                    ? `Auto-update stopped after ${match.sync_failures} failed refreshes in a row.`
                    : "Auto-update stopped: still unfinished long after its date."
                  : null}
                {match.unknown_platform_status && (
                  <span>
                    {" "}
                    Unknown {match.platform} state "{match.platform_status}";
                    kept as {match.status}.
                  </span>
                )}
              </div>
              <div className="text-muted-foreground mt-1 text-sm">
                Last refresh:{" "}
                {match.last_synced_at
                  ? formatDistanceToNow(new Date(match.last_synced_at), {
                      addSuffix: true,
                    })
                  : "never"}
              </div>
              {match.last_sync_error && (
                <div className="text-muted-foreground mt-1 break-all font-mono text-xs">
                  {match.last_sync_error}
                </div>
              )}
              {notes[match.id] && (
                <div className="text-muted-foreground mt-1 text-sm">
                  {notes[match.id]}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="cursor-pointer"
                disabled={busyId === match.id}
                onClick={() => retry(match)}
              >
                {busyId === match.id ? (
                  <Spinner className="h-4 w-4" />
                ) : (
                  "Retry"
                )}
              </Button>
              <Button
                size="sm"
                variant="destructive"
                className="cursor-pointer"
                disabled={busyId === match.id}
                onClick={() => cancel(match)}
              >
                Mark cancelled
              </Button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default SyncReview;
