import { Button } from "@/components/ui/button";
import {
  updatePlayerElo,
  resetPlayerElo,
  calculateTeamElos,
} from "@/services/api";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

function ControlPanel() {
  const [isUpdating, setIsUpdating] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
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
    setTimeout(() => setNotification(null), 5000);
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

  const handleCalculateTeamElos = async () => {
    if (
      !window.confirm(
        "Are you sure you want to calculate team ELOs based on player ELOs? This will override existing team ELO values.",
      )
    ) {
      return;
    }

    try {
      setIsCalculating(true);
      const result = await calculateTeamElos();
      showNotification(
        "success",
        "Team ELO Calculation Complete",
        `${result.updated_teams} teams updated. ${
          result.teams_without_enough_players || 0
        } teams without enough players.`,
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
        <Button
          className="cursor-pointer"
          variant="secondary"
          onClick={handleCalculateTeamElos}
          disabled={isCalculating}
        >
          {isCalculating ? (
            <>
              <Spinner className="mr-2 h-4 w-4" />
              Calculating...
            </>
          ) : (
            "Calculate Team Elo"
          )}
        </Button>
      </div>
    </div>
  );
}
export default ControlPanel;
