import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2, Trash2 } from "lucide-react";
import {
  clearDatabase,
  listCompetitions,
  deleteCompetition,
  type Competition,
} from "@/services/api";

function DeleteData() {
  const [securityKey, setSecurityKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [isLoadingCompetitions, setIsLoadingCompetitions] = useState(false);
  const [competitionSecurityKey, setCompetitionSecurityKey] = useState("");
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    loadCompetitions();
  }, []);

  const loadCompetitions = async () => {
    setIsLoadingCompetitions(true);
    try {
      const response = await listCompetitions();
      setCompetitions(response.competitions);
    } catch (error) {
      console.error("Failed to load competitions:", error);
    } finally {
      setIsLoadingCompetitions(false);
    }
  };

  const handleDeleteCompetition = async (
    competitionId: string,
    competitionName: string,
  ) => {
    if (
      !confirm(
        `Are you sure you want to delete the competition "${competitionName}" and ALL its data? This action cannot be undone!`,
      )
    ) {
      return;
    }

    setIsLoadingCompetitions(true);
    setResult(null);

    try {
      const response = await deleteCompetition(
        competitionId,
        competitionSecurityKey,
      );
      setResult({
        success: true,
        message: `${response.message}. Deleted ${response.total_records_deleted} total records.`,
      });
      // Reload competitions list
      await loadCompetitions();
      setCompetitionSecurityKey(""); // Clear the security key
    } catch (error: any) {
      setResult({
        success: false,
        message:
          error.response?.data?.error ||
          "Failed to delete competition. Please try again.",
      });
    } finally {
      setIsLoadingCompetitions(false);
    }
  };

  const handleClear = async () => {
    if (
      !confirm(
        "Are you sure you want to clear the database? This action cannot be undone!",
      )
    ) {
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const response = await clearDatabase(securityKey);
      setResult({
        success: true,
        message: response.message,
      });
    } catch (error: any) {
      setResult({
        success: false,
        message:
          error.response?.data?.error ||
          "Failed to clear database. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Delete Competitions Section */}
      <Card>
        <CardHeader>
          <CardTitle>Delete Competition</CardTitle>
          <CardDescription>
            Delete a specific competition and all its related data including
            matches, participants, events, and rankings. This action cannot be
            undone.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Input
                type="password"
                placeholder="Competition Security Key"
                value={competitionSecurityKey}
                onChange={(e) => setCompetitionSecurityKey(e.target.value)}
              />
              <p className="mt-1 text-sm text-gray-500">
                Enter the security key to delete competitions. Key is
                "confirm-delete-competition-789".
              </p>
            </div>

            {isLoadingCompetitions ? (
              <div className="py-4 text-center">Loading competitions...</div>
            ) : competitions.length === 0 ? (
              <div className="py-4 text-center text-gray-500">
                No competitions found
              </div>
            ) : (
              <div className="space-y-2">
                <h4 className="font-medium">Available Competitions:</h4>
                {competitions.map((competition) => (
                  <div
                    key={competition.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <h5 className="font-medium">{competition.name}</h5>
                      <p className="text-sm text-gray-500">
                        {competition.teams_count} teams,{" "}
                        {competition.matches_count} matches,{" "}
                        {competition.participants_count} participants
                      </p>
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() =>
                        handleDeleteCompetition(
                          competition.id,
                          competition.name,
                        )
                      }
                      disabled={
                        !competitionSecurityKey || isLoadingCompetitions
                      }
                    >
                      <Trash2 className="mr-1 h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {result && (
              <Alert variant={result.success ? "default" : "destructive"}>
                {result.success ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertTitle>{result.success ? "Success" : "Error"}</AlertTitle>
                <AlertDescription>{result.message}</AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Clear Database Section */}
      <Card>
        <CardHeader>
          <CardTitle>Clear Database</CardTitle>
          <CardDescription>
            Clear the database for testing purposes. This will delete all
            matches, participants, teams, players, events, and rankings, but
            will preserve seasons and competitions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Input
                type="password"
                placeholder="Security Key"
                value={securityKey}
                onChange={(e) => setSecurityKey(e.target.value)}
              />
              <p className="mt-1 text-sm text-gray-500">
                Enter the security key to clear the database. Key is
                "confirm-database-clear-123".
              </p>
            </div>

            {result && (
              <Alert variant={result.success ? "default" : "destructive"}>
                {result.success ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <AlertCircle className="h-4 w-4" />
                )}
                <AlertTitle>{result.success ? "Success" : "Error"}</AlertTitle>
                <AlertDescription>{result.message}</AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
        <CardFooter>
          <Button
            variant="destructive"
            onClick={handleClear}
            disabled={isLoading || !securityKey}
          >
            {isLoading ? "Clearing..." : "Clear Database"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

export default DeleteData;
