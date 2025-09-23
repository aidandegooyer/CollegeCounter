import { Button } from "@/components/ui/button";
import {
  updatePlayerElo,
  resetPlayerElo,
  calculateTeamElos,
  updateMatches,
  createRankingSnapshot,
  recalculateAllElos,
} from "@/services/api";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

function ControlPanel() {
  const [isUpdating, setIsUpdating] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [isUpdatingMatches, setIsUpdatingMatches] = useState(false);
  const [isCreatingSnapshot, setIsCreatingSnapshot] = useState(false);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    title: string;
    message: string;
  } | null>(null);

  const showNotification = (
    type: "success" | "error",
    title: string,
    message: string,
  ) => {
    setNotification({ type, title, message });
    // Clear notification after 5 seconds
    setTimeout(() => setNotification(null), 15000);
  };

  const handleUpdateElo = async () => {
    try {
      setIsUpdating(true);
      const result = await updatePlayerElo(import.meta.env.VITE_FACEIT_API_KEY);
      showNotification(
        "success",
        "ELO Update Complete",
        `${result.updated_players} players updated. ${result.not_found || 0} players not found.`,
      );
    } catch (error) {
      console.error("Error updating player ELO:", error);
      showNotification(
        "error",
        "Error",
        "There was an error updating player ELO values.",
      );
    } finally {
      setIsUpdating(false);
    }
  };

  const handleResetElo = async () => {
    if (
      !window.confirm(
        "Are you sure you want to reset all player ELO values to default?",
      )
    ) {
      return;
    }

    try {
      setIsResetting(true);
      const result = await resetPlayerElo();
      showNotification(
        "success",
        "ELO Reset Complete",
        `${result.updated_players} players reset to default ELO.`,
      );
    } catch (error) {
      console.error("Error resetting player ELO:", error);
      showNotification(
        "error",
        "Error",
        "There was an error resetting player ELO values.",
      );
    } finally {
      setIsResetting(false);
    }
  };

  const handleCalculateTeamElos = async (onlyDefaultElo: boolean = false) => {
    const confirmMessage = onlyDefaultElo
      ? "Are you sure you want to calculate team ELOs for teams with default ELO (1000) based on player ELOs?"
      : "Are you sure you want to calculate team ELOs based on player ELOs? This will override existing team ELO values.";

    if (!window.confirm(confirmMessage)) {
      return;
    }

    try {
      setIsCalculating(true);
      const result = await calculateTeamElos({
        only_default_elo: onlyDefaultElo,
        default_elo: 1000,
      });

      const actionType = onlyDefaultElo
        ? "for teams with default ELO"
        : "for all teams";
      showNotification(
        "success",
        "Team ELO Calculation Complete",
        `${result.updated_teams} teams updated ${actionType}. ${
          result.teams_without_enough_players || 0
        } teams without enough players. Total teams processed: ${result.total_teams_processed || 0}.`,
      );
    } catch (error) {
      console.error("Error calculating team ELOs:", error);
      showNotification(
        "error",
        "Error",
        "There was an error calculating team ELO values.",
      );
    } finally {
      setIsCalculating(false);
    }
  };

  const handleRecalculateAllElos = async () => {
    if (
      !window.confirm(
        "Are you sure you want to recalculate ALL ELOs from scratch? This will reset all team ELOs to 1000 and recalculate them based on all completed matches in chronological order. This process may take several minutes for large datasets.",
      )
    ) {
      return;
    }

    try {
      setIsRecalculating(true);
      const result = await recalculateAllElos({
        reset_to_default: false,
        default_elo: 1000,
      });
      showNotification(
        "success",
        "ELO Recalculation Complete",
        `${result.summary.processed_count} matches processed successfully. ${result.summary.error_count} errors occurred. ${result.total_elo_changes} total ELO changes made.`,
      );
    } catch (error) {
      console.error("Error recalculating ELOs:", error);
      showNotification(
        "error",
        "Error",
        "There was an error recalculating ELO values.",
      );
    } finally {
      setIsRecalculating(false);
    }
  };

  async function handleUpdateMatches(live?: boolean): Promise<void> {
    if (
      !window.confirm(
        "Are you sure you want to update match data? This will fetch the latest information from external APIs for scheduled and in-progress matches.",
      )
    ) {
      return;
    }

    try {
      setIsUpdatingMatches(true);
      const result = await updateMatches({
        auto_detect: !live,
        status_filter: live ? "in_progress" : "",
      });
      showNotification(
        "success",
        "Match Update Complete",
        `${result.updated_count} matches updated, ${result.error_count} errors. ${result.total_processed} matches processed.`,
      );
    } catch (error) {
      console.error("Error updating matches:", error);
      showNotification(
        "error",
        "Error",
        "There was an error updating match data.",
      );
    } finally {
      setIsUpdatingMatches(false);
    }
  }

  const handleCreateRankingSnapshot = async () => {
    if (
      !window.confirm(
        "Are you sure you want to create a ranking snapshot? This will capture the current team ELO rankings for historical tracking.",
      )
    ) {
      return;
    }

    try {
      setIsCreatingSnapshot(true);
      const result = await createRankingSnapshot();
      showNotification(
        "success",
        "Ranking Snapshot Created",
        `Successfully captured rankings for ${result.teams_ranked} teams in season "${result.season_name}".`,
      );
    } catch (error) {
      console.error("Error creating ranking snapshot:", error);
      showNotification(
        "error",
        "Error",
        "There was an error creating the ranking snapshot.",
      );
    } finally {
      setIsCreatingSnapshot(false);
    }
  };

  return (
    <div className="mt-4">
      <h2 className="text-4xl">Player Elo</h2>
      <hr></hr>

      {notification && (
        <Alert
          className={`mt-4 ${notification.type === "error" ? "bg-destructive/15" : ""}`}
        >
          <AlertTitle>{notification.title}</AlertTitle>
          <AlertDescription>{notification.message}</AlertDescription>
        </Alert>
      )}

      <div className="mt-4 flex gap-4">
        <Button
          className="text-foreground cursor-pointer"
          onClick={handleUpdateElo}
          disabled={isUpdating}
        >
          {isUpdating ? (
            <>
              <Spinner className="mr-2 h-4 w-4" />
              Updating...
            </>
          ) : (
            "Update Player Elo"
          )}
        </Button>
        <Button
          className="cursor-pointer"
          variant="destructive"
          onClick={handleResetElo}
          disabled={isResetting}
        >
          {isResetting ? (
            <>
              <Spinner className="mr-2 h-4 w-4" />
              Resetting...
            </>
          ) : (
            "Reset Player Elo"
          )}
        </Button>
      </div>
      <div className="mt-8">
        <h2 className="text-4xl">Team Elo</h2>
        <hr></hr>
        <div className="mt-4 flex gap-4">
          <Button
            className="cursor-pointer"
            variant="secondary"
            onClick={() => handleCalculateTeamElos(false)}
            disabled={isCalculating}
          >
            {isCalculating ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Calculating...
              </>
            ) : (
              "Calculate All Team ELOs"
            )}
          </Button>
          <Button
            className="cursor-pointer"
            variant="outline"
            onClick={() => handleCalculateTeamElos(true)}
            disabled={isCalculating}
          >
            {isCalculating ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Calculating...
              </>
            ) : (
              "Calculate Default ELO Teams Only"
            )}
          </Button>
          <Button
            className="cursor-pointer"
            variant="destructive"
            onClick={handleRecalculateAllElos}
            disabled={isRecalculating}
          >
            {isRecalculating ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Recalculating...
              </>
            ) : (
              "Recalculate All ELOs"
            )}
          </Button>
        </div>
      </div>
      <div className="mt-8">
        <h2 className="text-4xl">Matches</h2>
        <hr></hr>
        <div className="mt-4 flex gap-4">
          <Button
            className="cursor-pointer text-white"
            onClick={() => handleUpdateMatches(false)}
            disabled={isUpdatingMatches}
          >
            {isUpdatingMatches ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Updating...
              </>
            ) : (
              "Update Matches"
            )}
          </Button>
          <Button
            className="cursor-pointer text-white"
            onClick={() => handleUpdateMatches(true)}
            disabled={isUpdatingMatches}
          >
            {isUpdatingMatches ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Updating...
              </>
            ) : (
              "Update Live Matches"
            )}
          </Button>
        </div>
      </div>
      <div className="mt-8">
        <h2 className="text-4xl">Rankings</h2>
        <hr></hr>
        <div className="mt-4 flex gap-4">
          <Button
            className="cursor-pointer"
            variant="secondary"
            onClick={handleCreateRankingSnapshot}
            disabled={isCreatingSnapshot}
          >
            {isCreatingSnapshot ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Creating...
              </>
            ) : (
              "Create Ranking Snapshot"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
export default ControlPanel;
