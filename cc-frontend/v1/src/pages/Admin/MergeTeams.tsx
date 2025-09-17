import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useTeams } from "@/services/hooks";
import { mergeTeams } from "@/services/api";
import { AlertTriangle, Users, ArrowRight, CheckCircle } from "lucide-react";

interface MergeResponse {
  message: string;
  primary_team: {
    id: string;
    name: string;
    player_count: number;
  };
  secondary_team: {
    id: string;
    name: string;
    player_count: number;
  };
  merged_data: {
    players_moved: number;
    participants_merged: number;
    matches_updated: number;
  };
}

function MergeTeams() {
  const [primaryTeamId, setPrimaryTeamId] = useState<string>("");
  const [secondaryTeamId, setSecondaryTeamId] = useState<string>("");
  const [confirmText, setConfirmText] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<MergeResponse | null>(null);
  const [error, setError] = useState<string>("");

  const { data: teamsData } = useTeams();
  const teams: any[] = teamsData || [];

  const primaryTeam = teams.find((team: any) => team.id === primaryTeamId);
  const secondaryTeam = teams.find((team: any) => team.id === secondaryTeamId);

  const canMerge =
    primaryTeamId &&
    secondaryTeamId &&
    primaryTeamId !== secondaryTeamId &&
    confirmText.toLowerCase() === "merge teams";

  const handleMerge = async () => {
    if (!canMerge) return;

    setIsLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await mergeTeams({
        primary_team_id: primaryTeamId,
        secondary_team_id: secondaryTeamId,
      });

      setResult(data);

      // Reset form
      setPrimaryTeamId("");
      setSecondaryTeamId("");
      setConfirmText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="text-center">
        <h1 className="mb-2 text-3xl font-bold">Merge Teams</h1>
        <p className="text-gray-600">
          Combine two teams into one, preserving all players and match history
        </p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <Alert className="border-green-500 bg-green-50 text-green-700">
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">{result.message}</p>
              <div className="mt-4 grid grid-cols-1 gap-4 text-sm md:grid-cols-3">
                <div className="rounded bg-white p-3">
                  <p className="font-medium">Players Moved</p>
                  <p className="text-2xl font-bold text-green-600">
                    {result.merged_data.players_moved}
                  </p>
                </div>
                <div className="rounded bg-white p-3">
                  <p className="font-medium">Participants Merged</p>
                  <p className="text-2xl font-bold text-green-600">
                    {result.merged_data.participants_merged}
                  </p>
                </div>
                <div className="rounded bg-white p-3">
                  <p className="font-medium">Matches Updated</p>
                  <p className="text-2xl font-bold text-green-600">
                    {result.merged_data.matches_updated}
                  </p>
                </div>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Team Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Select Teams to Merge
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Primary Team */}
            <div className="space-y-2">
              <Label htmlFor="primary-team">
                Primary Team (will keep this team)
              </Label>
              <Select value={primaryTeamId} onValueChange={setPrimaryTeamId}>
                <SelectTrigger id="primary-team">
                  <SelectValue placeholder="Select primary team" />
                </SelectTrigger>
                <SelectContent>
                  {teams.map((team: any) => (
                    <SelectItem
                      key={team.id}
                      value={team.id}
                      disabled={team.id === secondaryTeamId}
                    >
                      <div className="flex items-center gap-2">
                        {team.picture && (
                          <img
                            src={team.picture}
                            alt={team.name}
                            className="h-6 w-6 rounded object-cover"
                          />
                        )}
                        <span>{team.name}</span>
                        {team.school_name && (
                          <span className="text-sm text-gray-500">
                            ({team.school_name})
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Secondary Team */}
            <div className="space-y-2">
              <Label htmlFor="secondary-team">
                Secondary Team (will be deleted)
              </Label>
              <Select
                value={secondaryTeamId}
                onValueChange={setSecondaryTeamId}
              >
                <SelectTrigger id="secondary-team">
                  <SelectValue placeholder="Select team to merge into primary" />
                </SelectTrigger>
                <SelectContent>
                  {teams.map((team: any) => (
                    <SelectItem
                      key={team.id}
                      value={team.id}
                      disabled={team.id === primaryTeamId}
                    >
                      <div className="flex items-center gap-2">
                        {team.picture && (
                          <img
                            src={team.picture}
                            alt={team.name}
                            className="h-6 w-6 rounded object-cover"
                          />
                        )}
                        <span>{team.name}</span>
                        {team.school_name && (
                          <span className="text-sm text-gray-500">
                            ({team.school_name})
                          </span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Confirmation */}
            <div className="space-y-2">
              <Label htmlFor="confirm">
                Type "merge teams" to confirm (this action cannot be undone)
              </Label>
              <Input
                id="confirm"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="merge teams"
                className="font-mono"
              />
            </div>
          </CardContent>
        </Card>

        {/* Preview */}
        <Card>
          <CardHeader>
            <CardTitle>Merge Preview</CardTitle>
          </CardHeader>
          <CardContent>
            {primaryTeam && secondaryTeam ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center space-x-4">
                  {/* Primary Team */}
                  <div className="rounded-lg border-2 border-green-500 bg-green-50 p-4 text-center">
                    <div className="mb-2 flex items-center justify-center gap-2">
                      {primaryTeam.picture && (
                        <img
                          src={primaryTeam.picture}
                          alt={primaryTeam.name}
                          className="h-8 w-8 rounded object-cover"
                        />
                      )}
                      <h3 className="font-semibold text-green-700">
                        {primaryTeam.name}
                      </h3>
                    </div>
                    <p className="text-sm text-green-600">Primary (Keep)</p>
                    <p className="text-sm">ELO: {primaryTeam.elo}</p>
                  </div>

                  <ArrowRight className="h-6 w-6 text-gray-400" />

                  {/* Secondary Team */}
                  <div className="rounded-lg border-2 border-red-500 bg-red-50 p-4 text-center">
                    <div className="mb-2 flex items-center justify-center gap-2">
                      {secondaryTeam.picture && (
                        <img
                          src={secondaryTeam.picture}
                          alt={secondaryTeam.name}
                          className="h-8 w-8 rounded object-cover"
                        />
                      )}
                      <h3 className="font-semibold text-red-700">
                        {secondaryTeam.name}
                      </h3>
                    </div>
                    <p className="text-sm text-red-600">Secondary (Delete)</p>
                    <p className="text-sm">ELO: {secondaryTeam.elo}</p>
                  </div>
                </div>

                <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                  <h4 className="mb-2 font-semibold text-yellow-800">
                    What will happen:
                  </h4>
                  <ul className="space-y-1 text-sm text-yellow-700">
                    <li>
                      • All players from "{secondaryTeam.name}" will be moved to
                      "{primaryTeam.name}"
                    </li>
                    <li>
                      • All participant records will be merged (competition
                      history preserved)
                    </li>
                    <li>
                      • All matches will be updated to reference "
                      {primaryTeam.name}"
                    </li>
                    <li>• The "{secondaryTeam.name}" team will be deleted</li>
                    <li>
                      • ELO and stats will be preserved on "{primaryTeam.name}"
                    </li>
                  </ul>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-gray-500">
                Select both teams to see merge preview
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Merge Button */}
      <div className="flex justify-center">
        <Button
          onClick={handleMerge}
          disabled={!canMerge || isLoading}
          size="lg"
          variant={canMerge ? "destructive" : "secondary"}
          className="min-w-48"
        >
          {isLoading ? (
            <>
              <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white"></div>
              Merging Teams...
            </>
          ) : (
            "Merge Teams"
          )}
        </Button>
      </div>

      {/* Warning */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <strong>Warning:</strong> This action cannot be undone. The secondary
          team will be permanently deleted, and all its data will be transferred
          to the primary team. Make sure you have a database backup before
          proceeding.
        </AlertDescription>
      </Alert>
    </div>
  );
}

export default MergeTeams;
