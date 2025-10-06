import { useState, useEffect } from "react";
import {
  fetchAllMatches,
  fetchAllTeams,
  fetchSeasons,
  listCompetitions,
  createMatch,
  updateMatch,
  deleteMatch,
} from "@/services/api";
import type {
  Match,
  Team,
  Season,
  Competition,
  CreateMatchRequest,
  UpdateMatchRequest,
} from "@/services/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import SearchSelect, {
  useSearchSelectOptions,
} from "@/components/SearchSelect";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { AlertCircle, Check, Plus, Trash2 } from "lucide-react";

function EditMatch() {
  const [activeTab, setActiveTab] = useState<"edit" | "create">("edit");
  const [matches, setMatches] = useState<Match[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Fetch all required data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [matchesData, teamsData, seasonsData, competitionsData] =
          await Promise.all([
            fetchAllMatches(),
            fetchAllTeams(),
            fetchSeasons(),
            listCompetitions(),
          ]);
        setMatches(matchesData);
        setTeams(teamsData);
        setSeasons(seasonsData);
        setCompetitions(competitionsData.competitions);
      } catch (error) {
        console.error("Error fetching data:", error);
        setNotification({
          type: "error",
          message: "Failed to load data",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Clear notification after 5 seconds
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const selectedMatch = matches.find((match) => match.id === selectedMatchId);

  const refreshMatches = async () => {
    try {
      const matchesData = await fetchAllMatches();
      setMatches(matchesData);
    } catch (error) {
      console.error("Error refreshing matches:", error);
    }
  };

  return (
    <div className="container mx-auto py-6">
      <h2 className="mb-6 text-3xl font-bold">Match Management</h2>

      {notification && (
        <div
          className={`mb-4 rounded p-4 ${
            notification.type === "success"
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {notification.type === "success" ? (
            <Check className="mr-2 inline" size={16} />
          ) : (
            <AlertCircle className="mr-2 inline" size={16} />
          )}
          {notification.message}
        </div>
      )}

      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as "edit" | "create")}
      >
        <TabsList className="mb-6 grid w-full grid-cols-2">
          <TabsTrigger value="edit">Edit Match</TabsTrigger>
          <TabsTrigger value="create">Create Match</TabsTrigger>
        </TabsList>

        <TabsContent value="edit">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle>Select Match</CardTitle>
                <CardDescription>
                  Choose a match to edit its details
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-4">
                    <Spinner />
                  </div>
                ) : (
                  <SearchSelect
                    options={[...matches]
                      .sort(
                        (a, b) =>
                          new Date(b.date).getTime() -
                          new Date(a.date).getTime(),
                      )
                      .map((match) => ({
                        value: match.id,
                        label: `${match.team1.name} vs ${match.team2.name} (${new Date(match.date).toLocaleDateString()})`,
                      }))}
                    value={selectedMatchId || ""}
                    onValueChange={setSelectedMatchId}
                    placeholder="Select a match"
                    searchPlaceholder="Search matches..."
                    allowClear
                  />
                )}
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Match Details</CardTitle>
                <CardDescription>Update the match information</CardDescription>
              </CardHeader>
              <CardContent>
                {selectedMatch ? (
                  <MatchEditForm
                    match={selectedMatch}
                    teams={teams}
                    seasons={seasons}
                    competitions={competitions}
                    setNotification={setNotification}
                    onMatchUpdated={refreshMatches}
                    onMatchDeleted={() => {
                      refreshMatches();
                      setSelectedMatchId(null);
                    }}
                  />
                ) : (
                  <p className="text-muted-foreground py-8 text-center">
                    Select a match to edit its details
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="create">
          <Card className="mx-auto max-w-2xl">
            <CardHeader>
              <CardTitle>Create New Match</CardTitle>
              <CardDescription>Add a new match to the database</CardDescription>
            </CardHeader>
            <CardContent>
              <MatchCreateForm
                teams={teams}
                seasons={seasons}
                competitions={competitions}
                setNotification={setNotification}
                onMatchCreated={refreshMatches}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

interface MatchEditFormProps {
  match: Match;
  teams: Team[];
  seasons: Season[];
  competitions: Competition[];
  setNotification: (
    notification: { type: "success" | "error"; message: string } | null,
  ) => void;
  onMatchUpdated: () => void;
  onMatchDeleted: () => void;
}

function MatchEditForm({
  match,
  teams,
  seasons,
  competitions,
  setNotification,
  onMatchUpdated,
  onMatchDeleted,
}: MatchEditFormProps) {
  const [formData, setFormData] = useState({
    team1_id: match.team1.id,
    team2_id: match.team2.id,
    date: match.date ? new Date(match.date).toISOString().slice(0, 16) : "",
    status: match.status as
      | "scheduled"
      | "in_progress"
      | "completed"
      | "cancelled",
    url: match.url || "",
    score_team1: match.score_team1,
    score_team2: match.score_team2,
    platform: match.platform as "faceit" | "playfly" | "other",
    season_id: "", // Will be set from match data
    competition_id: "", // Will be set from match data
    winner_id: match.winner?.id || "",
  });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Update form data when match changes
  useEffect(() => {
    setFormData({
      team1_id: match.team1.id,
      team2_id: match.team2.id,
      date: match.date ? new Date(match.date).toISOString().slice(0, 16) : "",
      status: match.status as
        | "scheduled"
        | "in_progress"
        | "completed"
        | "cancelled",
      url: match.url || "",
      score_team1: match.score_team1,
      score_team2: match.score_team2,
      platform: match.platform as "faceit" | "playfly" | "other",
      season_id: match.season?.id || "",
      competition_id: match.competition?.id || "",
      winner_id: match.winner?.id || "",
    });
  }, [match]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        name === "score_team1" || name === "score_team2"
          ? parseInt(value, 10) || 0
          : value,
    }));
  };

  const handleSelectChange = (value: string, name: string) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const updateData: UpdateMatchRequest = {
        team1_id: formData.team1_id,
        team2_id: formData.team2_id,
        date: formData.date || undefined,
        status: formData.status,
        url: formData.url || undefined,
        score_team1: formData.score_team1,
        score_team2: formData.score_team2,
        platform: formData.platform,
        season_id: formData.season_id || undefined,
        competition_id: formData.competition_id || undefined,
        winner_id: formData.winner_id || undefined,
      };

      await updateMatch(match.id, updateData);
      onMatchUpdated();
      setNotification({
        type: "success",
        message: "Match updated successfully",
      });
    } catch (error) {
      console.error("Error updating match:", error);
      setNotification({
        type: "error",
        message: "Failed to update match",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteMatch(match.id);
      onMatchDeleted();
      setNotification({
        type: "success",
        message: "Match deleted successfully",
      });
    } catch (error) {
      console.error("Error deleting match:", error);
      setNotification({
        type: "error",
        message: "Failed to delete match",
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="team1_id">Team 1</Label>
            <SearchSelect
              options={useSearchSelectOptions(teams, "name", "id")}
              value={formData.team1_id}
              onValueChange={(value) => handleSelectChange(value, "team1_id")}
              placeholder="Select Team 1"
              searchPlaceholder="Search teams..."
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="team2_id">Team 2</Label>
            <SearchSelect
              options={useSearchSelectOptions(teams, "name", "id")}
              value={formData.team2_id}
              onValueChange={(value) => handleSelectChange(value, "team2_id")}
              placeholder="Select Team 2"
              searchPlaceholder="Search teams..."
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="date">Date & Time</Label>
            <Input
              id="date"
              name="date"
              type="datetime-local"
              value={formData.date}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select
              value={formData.status}
              onValueChange={(value) => handleSelectChange(value, "status")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="scheduled">Scheduled</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="url">Match URL</Label>
          <Input
            id="url"
            name="url"
            type="url"
            value={formData.url}
            onChange={handleInputChange}
            placeholder="https://..."
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="score_team1">Team 1 Score</Label>
            <Input
              id="score_team1"
              name="score_team1"
              type="number"
              min="0"
              value={formData.score_team1}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="score_team2">Team 2 Score</Label>
            <Input
              id="score_team2"
              name="score_team2"
              type="number"
              min="0"
              value={formData.score_team2}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="platform">Platform</Label>
            <Select
              value={formData.platform}
              onValueChange={(value) => handleSelectChange(value, "platform")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="faceit">Faceit</SelectItem>
                <SelectItem value="playfly">Playfly</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="season_id">Season (Optional)</Label>
            <SearchSelect
              options={[
                { value: "", label: "No Season" },
                ...useSearchSelectOptions(seasons, "name", "id"),
              ]}
              value={formData.season_id}
              onValueChange={(value) => handleSelectChange(value, "season_id")}
              placeholder="Select season"
              searchPlaceholder="Search seasons..."
              allowClear
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="competition_id">Competition (Optional)</Label>
            <SearchSelect
              options={[
                { value: "", label: "No Competition" },
                ...useSearchSelectOptions(competitions, "name", "id"),
              ]}
              value={formData.competition_id}
              onValueChange={(value) =>
                handleSelectChange(value, "competition_id")
              }
              placeholder="Select competition"
              searchPlaceholder="Search competitions..."
              allowClear
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="winner_id">Winner (Optional)</Label>
          <Select
            value={formData.winner_id || "__no_winner__"}
            onValueChange={(value) => handleSelectChange(value, "winner_id")}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select winner" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__no_winner__">No Winner</SelectItem>
              <SelectItem value={formData.team1_id}>
                {teams.find((t) => t.id === formData.team1_id)?.name ||
                  "Team 1"}
              </SelectItem>
              <SelectItem value={formData.team2_id}>
                {teams.find((t) => t.id === formData.team2_id)?.name ||
                  "Team 2"}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button type="submit" className="flex-1" disabled={saving}>
            {saving ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Saving...
              </>
            ) : (
              "Save Match"
            )}
          </Button>

          <Button
            variant="destructive"
            disabled={deleting}
            onClick={() => {
              if (
                window.confirm(
                  "Are you sure you want to delete this match? This action cannot be undone.",
                )
              ) {
                handleDelete();
              }
            }}
          >
            {deleting ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Deleting...
              </>
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}

interface MatchCreateFormProps {
  teams: Team[];
  seasons: Season[];
  competitions: Competition[];
  setNotification: (
    notification: { type: "success" | "error"; message: string } | null,
  ) => void;
  onMatchCreated: () => void;
}

function MatchCreateForm({
  teams,
  seasons,
  competitions,
  setNotification,
  onMatchCreated,
}: MatchCreateFormProps) {
  const [formData, setFormData] = useState({
    team1_id: "",
    team2_id: "",
    date: "",
    status: "scheduled" as
      | "scheduled"
      | "in_progress"
      | "completed"
      | "cancelled",
    url: "",
    score_team1: 0,
    score_team2: 0,
    platform: "other" as "faceit" | "playfly" | "other",
    season_id: "",
    competition_id: "",
    winner_id: "",
  });
  const [creating, setCreating] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        name === "score_team1" || name === "score_team2"
          ? parseInt(value, 10) || 0
          : value,
    }));
  };

  const handleSelectChange = (value: string, name: string) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.team1_id || !formData.team2_id) {
      setNotification({
        type: "error",
        message: "Please select both teams",
      });
      return;
    }

    if (formData.team1_id === formData.team2_id) {
      setNotification({
        type: "error",
        message: "A team cannot play against itself",
      });
      return;
    }

    setCreating(true);

    try {
      const createData: CreateMatchRequest = {
        team1_id: formData.team1_id,
        team2_id: formData.team2_id,
        date: formData.date || undefined,
        status: formData.status,
        url: formData.url || undefined,
        score_team1: formData.score_team1,
        score_team2: formData.score_team2,
        platform: formData.platform,
        season_id: formData.season_id || undefined,
        competition_id: formData.competition_id || undefined,
        winner_id: formData.winner_id || undefined,
      };

      await createMatch(createData);
      onMatchCreated();
      setNotification({
        type: "success",
        message: "Match created successfully",
      });

      // Reset form
      setFormData({
        team1_id: "",
        team2_id: "",
        date: "",
        status: "scheduled",
        url: "",
        score_team1: 0,
        score_team2: 0,
        platform: "other",
        season_id: "",
        competition_id: "",
        winner_id: "",
      });
    } catch (error) {
      console.error("Error creating match:", error);
      setNotification({
        type: "error",
        message: "Failed to create match",
      });
    } finally {
      setCreating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="team1_id">Team 1 *</Label>
            <SearchSelect
              options={useSearchSelectOptions(teams, "name", "id")}
              value={formData.team1_id}
              onValueChange={(value) => handleSelectChange(value, "team1_id")}
              placeholder="Select Team 1"
              searchPlaceholder="Search teams..."
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="team2_id">Team 2 *</Label>
            <SearchSelect
              options={useSearchSelectOptions(teams, "name", "id")}
              value={formData.team2_id}
              onValueChange={(value) => handleSelectChange(value, "team2_id")}
              placeholder="Select Team 2"
              searchPlaceholder="Search teams..."
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="date">Date & Time</Label>
            <Input
              id="date"
              name="date"
              type="datetime-local"
              value={formData.date}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select
              value={formData.status}
              onValueChange={(value) => handleSelectChange(value, "status")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="scheduled">Scheduled</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="url">Match URL</Label>
          <Input
            id="url"
            name="url"
            type="url"
            value={formData.url}
            onChange={handleInputChange}
            placeholder="https://..."
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="score_team1">Team 1 Score</Label>
            <Input
              id="score_team1"
              name="score_team1"
              type="number"
              min="0"
              value={formData.score_team1}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="score_team2">Team 2 Score</Label>
            <Input
              id="score_team2"
              name="score_team2"
              type="number"
              min="0"
              value={formData.score_team2}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="platform">Platform</Label>
            <Select
              value={formData.platform}
              onValueChange={(value) => handleSelectChange(value, "platform")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="faceit">Faceit</SelectItem>
                <SelectItem value="playfly">Playfly</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="season_id">Season (Optional)</Label>
            <SearchSelect
              options={[
                { value: "", label: "No Season" },
                ...useSearchSelectOptions(seasons, "name", "id"),
              ]}
              value={formData.season_id}
              onValueChange={(value) => handleSelectChange(value, "season_id")}
              placeholder="Select season"
              searchPlaceholder="Search seasons..."
              allowClear
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="competition_id">Competition (Optional)</Label>
            <SearchSelect
              options={[
                { value: "", label: "No Competition" },
                ...useSearchSelectOptions(competitions, "name", "id"),
              ]}
              value={formData.competition_id}
              onValueChange={(value) =>
                handleSelectChange(value, "competition_id")
              }
              placeholder="Select competition"
              searchPlaceholder="Search competitions..."
              allowClear
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="winner_id">Winner (Optional)</Label>
          <Select
            value={formData.winner_id || "__no_winner__"}
            onValueChange={(value) => handleSelectChange(value, "winner_id")}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select winner" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__no_winner__">No Winner</SelectItem>
              {formData.team1_id && (
                <SelectItem value={formData.team1_id}>
                  {teams.find((t) => t.id === formData.team1_id)?.name ||
                    "Team 1"}
                </SelectItem>
              )}
              {formData.team2_id && (
                <SelectItem value={formData.team2_id}>
                  {teams.find((t) => t.id === formData.team2_id)?.name ||
                    "Team 2"}
                </SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>

        <Button type="submit" className="w-full" disabled={creating}>
          {creating ? (
            <>
              <Spinner className="mr-2 h-4 w-4" />
              Creating...
            </>
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Create Match
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

export default EditMatch;
