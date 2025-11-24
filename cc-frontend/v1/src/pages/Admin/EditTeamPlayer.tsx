import { useState, useEffect } from "react";
import { fetchAllTeams, fetchAllPlayers } from "@/services/api";
import {
  updateTeam,
  uploadTeamPicture,
  updatePlayer,
  uploadPlayerPicture,
  importTeamFromFaceit,
} from "@/services/api-team-player-edit";
import type { Team, Player } from "@/services/api";
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
import SearchSelect, {
  useSearchSelectOptions,
} from "@/components/SearchSelect";
import { Spinner } from "@/components/ui/shadcn-io/spinner";
import { AlertCircle, Check, Upload } from "lucide-react";
import imageCompression from "browser-image-compression";

function EditTeamPlayer() {
  const [activeTab, setActiveTab] = useState<"teams" | "players" | "create">(
    "teams",
  );
  const [teams, setTeams] = useState<Team[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Fetch teams and players
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [teamsData, playersData] = await Promise.all([
          fetchAllTeams(),
          fetchAllPlayers(),
        ]);
        setTeams(teamsData);
        setPlayers(playersData);
      } catch (error) {
        console.error("Error fetching data:", error);
        setNotification({
          type: "error",
          message: "Failed to load teams and players",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Selected entity details
  const selectedTeam = teams.find((team) => team.id === selectedTeamId);
  const selectedPlayer = players.find(
    (player) => player.id === selectedPlayerId,
  );

  return (
    <div className="container mx-auto py-6">
      <h2 className="mb-6 text-3xl font-bold">Edit Teams & Players</h2>

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
        onValueChange={(v) => setActiveTab(v as "teams" | "players" | "create")}
      >
        <TabsList className="mb-6 grid w-full grid-cols-3">
          <TabsTrigger value="teams">Edit Teams</TabsTrigger>
          <TabsTrigger value="players">Edit Players</TabsTrigger>
          <TabsTrigger value="create">Create Team</TabsTrigger>
        </TabsList>

        <TabsContent value="teams">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle>Select Team</CardTitle>
                <CardDescription>
                  Choose a team to edit its details
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-4">
                    <Spinner />
                  </div>
                ) : (
                  <SearchSelect
                    options={useSearchSelectOptions(
                      [...teams].sort((a, b) => a.name.localeCompare(b.name)),
                      "name",
                      "id",
                    )}
                    value={selectedTeamId || ""}
                    onValueChange={setSelectedTeamId}
                    placeholder="Select a team"
                    searchPlaceholder="Search teams..."
                    allowClear
                  />
                )}
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Team Details</CardTitle>
                <CardDescription>Update the team's information</CardDescription>
              </CardHeader>
              <CardContent>
                {selectedTeam ? (
                  <TeamEditForm
                    team={selectedTeam}
                    setNotification={setNotification}
                  />
                ) : (
                  <p className="text-muted-foreground py-8 text-center">
                    Select a team to edit its details
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="players">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <Card className="md:col-span-1">
              <CardHeader>
                <CardTitle>Select Player</CardTitle>
                <CardDescription>
                  Choose a player to edit their details
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-4">
                    <Spinner />
                  </div>
                ) : (
                  <SearchSelect
                    options={[...players]
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map((player) => ({
                        value: player.id,
                        label: `${player.name}${player.team ? ` (${player.team.name})` : ""}`,
                      }))}
                    value={selectedPlayerId || ""}
                    onValueChange={setSelectedPlayerId}
                    placeholder="Select a player"
                    searchPlaceholder="Search players..."
                    allowClear
                  />
                )}
              </CardContent>
            </Card>

            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Player Details</CardTitle>
                <CardDescription>
                  Update the player's information
                </CardDescription>
              </CardHeader>
              <CardContent>
                {selectedPlayer ? (
                  <PlayerEditForm
                    player={selectedPlayer}
                    teams={teams}
                    setNotification={setNotification}
                  />
                ) : (
                  <p className="text-muted-foreground py-8 text-center">
                    Select a player to edit their details
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="create">
          <CreateTeamFromFaceit setNotification={setNotification} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

interface TeamEditFormProps {
  team: Team;
  setNotification: (
    notification: { type: "success" | "error"; message: string } | null,
  ) => void;
}

function TeamEditForm({ team, setNotification }: TeamEditFormProps) {
  const [formData, setFormData] = useState({
    name: team.name,
    school_name: team.school_name || "",
    elo: team.elo,
  });
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(
    team.picture || null,
  );
  const [saving, setSaving] = useState(false);

  // Update form data when team changes
  useEffect(() => {
    setFormData({
      name: team.name,
      school_name: team.school_name || "",
      elo: team.elo,
    });
    setPreviewUrl(team.picture || null);
    setFileToUpload(null);
  }, [team]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "elo" ? parseInt(value, 10) || 0 : value,
    }));
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const options = {
        maxSizeMB: 0.5,
        maxWidthOrHeight: 512,
        useWebWorker: true,
        preserveExif: false,
      };
      try {
        const compressedFile = await imageCompression(file, options);

        const ext = file.name.split(".").pop();
        const fixedFile = new File([compressedFile], `compressed.${ext}`, {
          type: compressedFile.type,
        });

        setFileToUpload(fixedFile);
        setPreviewUrl(URL.createObjectURL(compressedFile));
      } catch (error) {
        alert("Image compression failed");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const updateData = {
        name: formData.name,
        school_name: formData.school_name || undefined,
        elo: formData.elo,
      };

      // If there's a new image, upload it to Firebase and update all data in one call
      if (fileToUpload) {
        await uploadTeamPicture(team.id, fileToUpload, updateData);
      } else {
        // If no new image, just update the team data
        await updateTeam(team.id, updateData);
      }

      // Show success notification
      setNotification({
        type: "success",
        message: "Team updated successfully",
      });
    } catch (error) {
      console.error("Error updating team:", error);
      setNotification({
        type: "error",
        message: "Failed to update team",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-4">
        <div className="mb-4 flex flex-col items-center">
          <div className="relative mb-2 flex h-32 w-32 items-center justify-center overflow-hidden rounded-lg border-2 border-dashed">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={formData.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <Upload className="text-muted-foreground h-8 w-8" />
            )}
          </div>
          <Label htmlFor="team-picture" className="cursor-pointer">
            <span className="text-sm text-blue-500">
              {team.picture ? "Change Picture" : "Upload Picture"}
            </span>
            <Input
              id="team-picture"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </Label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Team Name</Label>
            <Input
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="school_name">School Name</Label>
            <Input
              id="school_name"
              name="school_name"
              value={formData.school_name}
              onChange={handleInputChange}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="elo">Team ELO</Label>
          <Input
            id="elo"
            name="elo"
            type="number"
            value={formData.elo}
            onChange={handleInputChange}
            required
          />
        </div>

        <Button type="submit" className="w-full" disabled={saving}>
          {saving ? (
            <>
              <Spinner className="mr-2 h-4 w-4" />
              Saving...
            </>
          ) : (
            "Save Team"
          )}
        </Button>
      </div>
    </form>
  );
}

interface PlayerEditFormProps {
  player: Player;
  teams: Team[];
  setNotification?: (
    notification: { type: "success" | "error"; message: string } | null,
  ) => void;
}

function PlayerEditForm({
  player,
  teams,
  setNotification,
}: PlayerEditFormProps) {
  const [formData, setFormData] = useState({
    name: player.name,
    steam_id: player.steam_id || "",
    faceit_id: player.faceit_id || "",
    elo: player.elo,
    skill_level: player.skill_level,
    team_id: player.team?.id || "",
    benched: player.benched,
    visible: player.visible,
  });
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(
    player.picture || null,
  );
  const [saving, setSaving] = useState(false);

  // Update form data when player changes
  useEffect(() => {
    setFormData({
      name: player.name,
      steam_id: player.steam_id || "",
      faceit_id: player.faceit_id || "",
      elo: player.elo,
      skill_level: player.skill_level,
      team_id: player.team?.id || "",
      benched: player.benched,
      visible: player.visible,
    });
    setPreviewUrl(player.picture || null);
    setFileToUpload(null);
  }, [player]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        type === "checkbox"
          ? checked
          : name === "elo" || name === "skill_level"
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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const options = {
        maxSizeMB: 0.5,
        maxWidthOrHeight: 512,
        useWebWorker: true,
        preserveExif: false,
      };
      try {
        const compressedFile = await imageCompression(file, options);

        const ext = file.name.split(".").pop();
        const fixedFile = new File([compressedFile], `compressed.${ext}`, {
          type: compressedFile.type,
        });

        setFileToUpload(fixedFile);
        setPreviewUrl(URL.createObjectURL(compressedFile));
      } catch (error) {
        alert("Image compression failed");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const updateData = {
        name: formData.name,
        steam_id: formData.steam_id || undefined,
        faceit_id: formData.faceit_id || undefined,
        elo: formData.elo,
        skill_level: formData.skill_level,
        team_id: formData.team_id || null,
        benched: formData.benched,
        visible: formData.visible,
      };

      // If there's a new image, upload it to Firebase and update all data in one call
      if (fileToUpload) {
        await uploadPlayerPicture(player.id, fileToUpload, updateData);
      } else {
        // If no new image, just update the player data
        await updatePlayer(player.id, updateData);
      }

      // Show success notification
      if (setNotification) {
        setNotification({
          type: "success",
          message: "Player updated successfully",
        });
      }
    } catch (error) {
      console.error("Error updating player:", error);
      if (setNotification) {
        setNotification({
          type: "error",
          message: "Failed to update player",
        });
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-4">
        <div className="mb-4 flex flex-col items-center">
          <div className="relative mb-2 flex h-32 w-32 items-center justify-center overflow-hidden rounded-lg border-2 border-dashed">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt={formData.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <Upload className="text-muted-foreground h-8 w-8" />
            )}
          </div>
          <Label htmlFor="player-picture" className="cursor-pointer">
            <span className="text-sm text-blue-500">
              {player.picture ? "Change Picture" : "Upload Picture"}
            </span>
            <Input
              id="player-picture"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </Label>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="name">Player Name</Label>
            <Input
              id="name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="team_id">Team</Label>
            <SearchSelect
              options={[
                { value: "", label: "No Team" },
                ...useSearchSelectOptions(teams, "name", "id"),
              ]}
              value={formData.team_id}
              onValueChange={(value) => handleSelectChange(value, "team_id")}
              placeholder="Select a team"
              searchPlaceholder="Search teams..."
              allowClear
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="steam_id">Steam ID</Label>
            <Input
              id="steam_id"
              name="steam_id"
              value={formData.steam_id}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="faceit_id">Faceit ID</Label>
            <Input
              id="faceit_id"
              name="faceit_id"
              value={formData.faceit_id}
              onChange={handleInputChange}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="elo">Player ELO</Label>
            <Input
              id="elo"
              name="elo"
              type="number"
              value={formData.elo}
              onChange={handleInputChange}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="skill_level">Skill Level (1-10)</Label>
            <Input
              id="skill_level"
              name="skill_level"
              type="number"
              min="1"
              max="10"
              value={formData.skill_level}
              onChange={handleInputChange}
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-2">
            <Input
              id="benched"
              name="benched"
              type="checkbox"
              checked={formData.benched}
              onChange={handleInputChange}
              className="h-4 w-4"
            />
            <Label htmlFor="benched">Benched</Label>
          </div>
          <div className="flex items-center space-x-2">
            <Input
              id="visible"
              name="visible"
              type="checkbox"
              checked={formData.visible}
              onChange={handleInputChange}
              className="h-4 w-4"
            />
            <Label htmlFor="visible">Visible</Label>
          </div>
        </div>

        <Button type="submit" className="w-full" disabled={saving}>
          {saving ? (
            <>
              <Spinner className="mr-2 h-4 w-4" />
              Saving...
            </>
          ) : (
            "Save Player"
          )}
        </Button>
      </div>
    </form>
  );
}

interface CreateTeamFromFaceitProps {
  setNotification: (
    notification: { type: "success" | "error"; message: string } | null,
  ) => void;
}

function CreateTeamFromFaceit({ setNotification }: CreateTeamFromFaceitProps) {
  const [faceitUrl, setFaceitUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    team: { id: string; name: string; picture: string; elo: number };
    players: Array<{ id: string; name: string; existed: boolean }>;
  } | null>(null);

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!faceitUrl.trim()) {
      setNotification({
        type: "error",
        message: "Please enter a Faceit team URL",
      });
      return;
    }

    setImporting(true);
    setImportResult(null);

    try {
      const response = await importTeamFromFaceit({ team_url: faceitUrl });

      setImportResult({
        team: response.team,
        players: response.players,
      });

      setNotification({
        type: "success",
        message: `Team "${response.team.name}" imported successfully with ${response.players.length} players`,
      });

      // Clear the form
      setFaceitUrl("");
    } catch (error: any) {
      console.error("Error importing team:", error);
      const errorMessage =
        error.response?.data?.error || "Failed to import team from Faceit";
      setNotification({
        type: "error",
        message: errorMessage,
      });
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Import Team from Faceit</CardTitle>
          <CardDescription>
            Create a new team by importing data from Faceit. Enter the team's
            Faceit URL to automatically import team details and roster.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleImport} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="faceit-url">Faceit Team URL</Label>
              <Input
                id="faceit-url"
                type="text"
                placeholder="https://www.faceit.com/en/teams/abc123-team-name"
                value={faceitUrl}
                onChange={(e) => setFaceitUrl(e.target.value)}
                disabled={importing}
              />
              <p className="text-muted-foreground text-sm">
                You can find the team URL on the team's Faceit profile page
              </p>
            </div>

            <Button type="submit" className="w-full" disabled={importing}>
              {importing ? (
                <>
                  <Spinner className="mr-2 h-4 w-4" />
                  Importing Team...
                </>
              ) : (
                "Import Team"
              )}
            </Button>
          </form>

          {importResult && (
            <div className="mt-6 space-y-4">
              <div className="rounded-lg border p-4">
                <h3 className="mb-2 font-semibold">Team Created</h3>
                <div className="flex items-center gap-3">
                  {importResult.team.picture && (
                    <img
                      src={importResult.team.picture}
                      alt={importResult.team.name}
                      className="h-12 w-12 rounded"
                    />
                  )}
                  <div>
                    <p className="font-medium">{importResult.team.name}</p>
                    <p className="text-muted-foreground text-sm">
                      ELO: {importResult.team.elo}
                    </p>
                  </div>
                </div>
              </div>

              {importResult.players.length > 0 && (
                <div className="rounded-lg border p-4">
                  <h3 className="mb-2 font-semibold">
                    Players ({importResult.players.length})
                  </h3>
                  <div className="space-y-1">
                    {importResult.players.map((player) => (
                      <div
                        key={player.id}
                        className="text-muted-foreground flex items-center justify-between text-sm"
                      >
                        <span>{player.name}</span>
                        {player.existed && (
                          <span className="text-xs italic">(existing)</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default EditTeamPlayer;
