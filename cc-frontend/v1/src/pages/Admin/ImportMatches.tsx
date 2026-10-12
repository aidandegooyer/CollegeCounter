import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import {
  fetchSeasons,
  createSeason,
  createEvent,
  importMatches,
  fetchFaceitMatches,
  fetchAllTeams,
  resolveImportTeams,
  fetchLeagueSpotSeason,
  fetchLeagueSpotStage,
  fetchLeagueSpotRoundMatches,
  fetchLeagueSpotMatch,
  fetchLeagueSpotParticipants,
  fetchAllEvents,
  fetchRegentsLeagueMatches,
} from "@/services/api";

import type {
  Season,
  Team,
  PublicEvent,
  ImportMatchesRequest,
  ResolvedImportTeam,
} from "@/services/api";

function SelectPlatform({
  platform,
  setPlatform,
}: {
  platform: string;
  setPlatform: (platform: string) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Platform</h1>
      <RadioGroup value={platform} onValueChange={setPlatform}>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="faceit" id="faceit" />
          <Label htmlFor="faceit">Faceit</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="leaguespot" id="leaguespot" />
          <Label htmlFor="leaguespot">Leaguespot</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="regentsleague" id="regentsleague" />
          <Label htmlFor="regentsleague">Regents League</Label>
        </div>
      </RadioGroup>
    </div>
  );
}

// Function to convert LeagueSpot data to our schema format
function convertLeagueSpotDataToSchema(leagueSpotData: any): any {
  if (!leagueSpotData || !leagueSpotData.matches) {
    return { items: [] };
  }

  const convertedMatches = leagueSpotData.matches
    .map((match: any, index: number) => {
      // Extract team information from participants
      const teams = match.participants || [];
      const team1 = teams[0] || {};
      const team2 = teams[1] || {};

      // Extract round information for event imports
      const roundInfo = match._round_info || {};

      const team1Name = team1.name || "Unknown Team 1";
      const team2Name = team2.name || "Unknown Team 2";

      return {
        match_id: match.id,
        competition_id: match.leagueId || "",
        competition_name: leagueSpotData.season?.name || "Unknown Competition",
        region: "",
        status: getMatchStatus(match.currentState),
        scheduled_at: match.startTimeUtc,
        finished_at: match.currentState === 3 ? match.startTimeUtc : null, // Assuming state 3 is finished
        results: {
          winner:
            match.winner ||
            (match.currentState === 3
              ? teams[0]?.gameWins > teams[1]?.gameWins
                ? "faction1"
                : "faction2"
              : null),
          score: {
            faction1: team1.gameWins || 0,
            faction2: team2.gameWins || 0,
          },
        },
        teams: {
          faction1: {
            faction_id: team1.teamId || team1.id,
            name: team1Name,
            avatar: team1.avatarUrl || "",
            roster: convertPlayersToFaceitFormat(team1.users || []),
          },
          faction2: {
            faction_id: team2.teamId || team2.id,
            name: team2Name,
            avatar: team2.avatarUrl || "",
            roster: convertPlayersToFaceitFormat(team2.users || []),
          },
        },
        voting: null,
        maps: [],
        // Add round metadata for event bracket imports
        _event_match_metadata: roundInfo.id
          ? {
              round: roundInfo.sortOrder || 0,
              round_name: roundInfo.name || "",
              round_state: roundInfo.currentState || 0,
              best_of: roundInfo.bestOf || 1,
              // Calculate position within bracket based on match index within round
              // This will be refined by backend based on all matches in the round
              num_in_bracket: index + 1,
            }
          : null,
        // Add original LeagueSpot data for debugging
        _leaguespot_original: match,
      };
    })
    .filter((match: any) => {
      // Skip matches with unknown teams (TBD matches to be imported later)
      const team1Name = match.teams.faction1.name.toLowerCase();
      const team2Name = match.teams.faction2.name.toLowerCase();

      const unknownTeamNames = [
        "unknown team 1",
        "unknown team 2",
        "tbd",
        "bye",
      ];

      if (
        unknownTeamNames.includes(team1Name) ||
        unknownTeamNames.includes(team2Name)
      ) {
        console.log(
          `Skipping match ${match.match_id} with unknown/TBD teams: ${match.teams.faction1.name} vs ${match.teams.faction2.name}`,
        );
        return false;
      }

      return true;
    });

  return {
    items: convertedMatches,
    // Preserve original data structure for reference
    _leaguespot_raw: leagueSpotData,
  };
}

// Helper function to convert match state to status
function getMatchStatus(currentState: number): string {
  switch (currentState) {
    case 0:
      return "SCHEDULED";
    case 1:
      return "READY";
    case 2:
      return "ONGOING";
    case 3:
      return "FINISHED";
    case 4:
      return "ABORTED";
    case 5:
      return "CANCELLED";
    default:
      return "UNKNOWN";
  }
}

// Helper function to convert LeagueSpot users to Faceit roster format
function convertPlayersToFaceitFormat(users: any[]): any[] {
  return users
    .filter((user: any) => {
      // Skip coaches (teamRoleId: "6f4da22c-7fe5-4c78-8876-eec2c87d1096")
      return user.teamRoleId !== "6f4da22c-7fe5-4c78-8876-eec2c87d1096";
    })
    .map((user: any) => {
      // Determine if player is captain (teamRoleId: "5a1675f0-2fa9-482b-b187-434901734a42")
      const isCaptain =
        user.teamRoleId === "5a1675f0-2fa9-482b-b187-434901734a42";

      return {
        player_id: user.userId || user.id,
        nickname: user.gamerHandle || user.firstName || "Unknown Player",
        avatar: user.avatarUrl || "",
        membership: user.teamRoleId || "",
        game_player_id: user.gameHandle?.providerUserId || "",
        game_player_name:
          user.gamerHandle || user.firstName || "Unknown Player",
        game_skill_level: user.gameRanking?.numericValue || 0,
        faceit_url: "",
        // Add captain flag for easier identification
        is_captain: isCaptain,
        // Store original user data
        _leaguespot_original: user,
      };
    });
}

// Function to fetch all Playfly matches using LeagueSpot API
// This function reverse engineers the LeagueSpot API to import Playfly matches:
// For Season ID:
// 1. Get season info from seasonId to find currentStageId
// 2. Get stage info to find all rounds
// For Stage ID:
// 1. Get stage info directly
// 2. Find all rounds
// Then:
// 3. Get matches from each round
// 4. Get detailed match data and participants for each match
// 5. Return comprehensive match data for import
async function fetchPlayflyMatchesViaLeagueSpot(
  idValue: string,
  idType: "season" | "stage" = "season",
): Promise<any> {
  if (!idValue || idValue.trim() === "") {
    throw new Error(
      `${idType === "season" ? "Season" : "Stage"} ID is required`,
    );
  }

  try {
    let seasonData = null;
    let stageData = null;
    let stageId = "";

    if (idType === "season") {
      // Step 1: Get season info to get currentStageId
      console.log(`Fetching season data for: ${idValue}`);
      seasonData = await fetchLeagueSpotSeason(idValue);
      stageId = seasonData.currentStageId;

      if (!stageId) {
        throw new Error("No current stage found for this season");
      }

      // Step 2: Get stage info to get rounds
      console.log(`Fetching stage data for: ${stageId}`);
      stageData = await fetchLeagueSpotStage(stageId);
    } else {
      // Direct stage ID provided - fetch stage info directly
      stageId = idValue;
      console.log(`Fetching stage data directly for: ${stageId}`);
      stageData = await fetchLeagueSpotStage(stageId);

      // Optionally fetch season data if available
      if (stageData.seasonId) {
        try {
          seasonData = await fetchLeagueSpotSeason(stageData.seasonId);
        } catch (error) {
          console.warn("Could not fetch season data:", error);
        }
      }
    }

    const rounds = stageData.rounds || [];

    if (rounds.length === 0) {
      throw new Error("No rounds found for this stage");
    }

    console.log(`Found ${rounds.length} rounds in stage`);

    // Step 3: Get all matches from all rounds
    let allMatches: any[] = [];

    for (const round of rounds) {
      try {
        console.log(`Fetching matches for round: ${round.id} (${round.name})`);
        const roundMatches = await fetchLeagueSpotRoundMatches(round.id);

        // Attach round metadata to each match for later processing
        const matchesWithRoundInfo = roundMatches.map((match: any) => ({
          ...match,
          _round_info: {
            id: round.id,
            name: round.name,
            sortOrder: round.sortOrder,
            currentState: round.currentState,
            bestOf: round.bestOf,
          },
        }));

        allMatches = allMatches.concat(matchesWithRoundInfo);
        console.log(
          `Found ${roundMatches.length} matches in round ${round.name}`,
        );
      } catch (error) {
        console.warn(`Failed to fetch matches for round ${round.id}:`, error);
        // Continue with other rounds even if one fails
      }
    }

    console.log(`Total matches found: ${allMatches.length}`);

    // Step 4: Get detailed match data and participants for each match
    const detailedMatches = [];

    const matchesToProcess = Math.min(allMatches.length);

    for (let i = 0; i < matchesToProcess; i++) {
      const match = allMatches[i];
      try {
        console.log(
          `Fetching details for match ${i + 1}/${allMatches.length}: ${match.id}`,
        );

        // Get detailed match data
        const matchDetails = await fetchLeagueSpotMatch(match.id);

        // Get participants data
        const participants = await fetchLeagueSpotParticipants(match.id);

        // Combine the data, preserving round metadata
        detailedMatches.push({
          ...matchDetails,
          participants: participants,
          // Keep round info for backend processing
          _round_info: match._round_info,
          // Keep original match data as backup
          originalMatch: match,
        });
      } catch (error) {
        console.warn(`Failed to fetch details for match ${match.id}:`, error);
        // Add the basic match data even if details fail
        detailedMatches.push({
          ...match,
          participants: [],
          error: `Failed to fetch detailed data: ${error}`,
        });
      }
    }

    console.log(`Successfully processed ${detailedMatches.length} matches`);

    const rawLeagueSpotData = {
      season: seasonData,
      stage: stageData,
      matches: detailedMatches,
      totalMatches: detailedMatches.length,
    };

    // Convert LeagueSpot data to our schema format (compatible with Faceit import flow)
    const convertedData = convertLeagueSpotDataToSchema(rawLeagueSpotData);

    console.log(
      `Converted to schema format with ${convertedData.items.length} matches`,
    );

    return convertedData;
  } catch (error) {
    console.error("Error fetching Playfly matches via LeagueSpot:", error);
    throw error;
  }
}

function SelectLeagueOrEvent({
  eventType,
  setEventType,
}: {
  eventType: string;
  setEventType: (type: string) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Type</h1>
      <RadioGroup value={eventType} onValueChange={setEventType}>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="event" id="event" />
          <Label htmlFor="event">Event (Bracket based)</Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="league" id="league" />
          <Label htmlFor="league">League</Label>
        </div>
      </RadioGroup>
    </div>
  );
}

function SelectOrCreateSeason({
  seasons,
  selectedSeason,
  setSelectedSeason,
  setShowCreateSeason,
}: {
  seasons: Season[];
  selectedSeason: string;
  setSelectedSeason: (seasonId: string) => void;
  setShowCreateSeason: (show: boolean) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select Season</h1>
      <Select value={selectedSeason} onValueChange={setSelectedSeason}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Season" />
        </SelectTrigger>
        <SelectContent>
          {(Array.isArray(seasons) ? seasons : []).map((season) => (
            <SelectItem key={season.id} value={season.id}>
              {season.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button variant="outline" onClick={() => setShowCreateSeason(true)}>
        Create New Season
      </Button>
    </div>
  );
}

function CreateSeasonForm({
  onCancel,
  onSuccess,
}: {
  onCancel: () => void;
  onSuccess: (season: Season) => void;
}) {
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const newSeason = await createSeason(name, startDate, endDate);
      onSuccess(newSeason);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to create season");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Create New Season</h1>
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-4">
        <div>
          <Label htmlFor="name">Season Name</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="startDate">Start Date</Label>
          <Input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="endDate">End Date</Label>
          <Input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>
        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Creating..." : "Create Season"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function CreateEventForm({
  onCancel,
  onSuccess,
  selectedSeason,
}: {
  onCancel: () => void;
  onSuccess: (eventId: string, eventName: string) => void;
  selectedSeason: string;
}) {
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [description, setDescription] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const newEvent = await createEvent({
        name,
        start_date: startDate,
        end_date: endDate,
        description,
        season_id: selectedSeason,
      });
      onSuccess(newEvent.id, newEvent.name);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to create event");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Create New Event</h1>
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-4">
        <div>
          <Label htmlFor="name">Event Name</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="description">Description (Optional)</Label>
          <Input
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="startDate">Start Date</Label>
          <Input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="endDate">End Date</Label>
          <Input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>
        <div className="flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Creating..." : "Create Event"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function SelectOrCreateEvent({
  events,
  selectedEvent,
  setSelectedEvent,
  setShowCreateEvent,
}: {
  events: PublicEvent[];
  selectedEvent: string;
  setSelectedEvent: (eventId: string, eventName: string) => void;
  setShowCreateEvent: (show: boolean) => void;
}) {
  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Select or Create Event</h1>
      {events.length > 0 ? (
        <>
          <div className="w-full max-w-md">
            <Label htmlFor="eventSelect">Select an Existing Event</Label>
            <Select
              value={selectedEvent}
              onValueChange={(value) => {
                const event = events.find((e) => e.id === value);
                if (event) {
                  setSelectedEvent(event.id, event.name);
                }
              }}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Choose an event" />
              </SelectTrigger>
              <SelectContent>
                {events.map((event) => (
                  <SelectItem key={event.id} value={event.id}>
                    {event.name} (
                    {new Date(event.start_date).toLocaleDateString()})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="text-sm text-gray-500">or</div>
        </>
      ) : (
        <p className="text-sm text-gray-500">No existing events found</p>
      )}
      <Button onClick={() => setShowCreateEvent(true)}>Create New Event</Button>
    </div>
  );
}

function MetadataForm({
  competitionName,
  setCompetitionName,
  championshipId,
  setChampionshipId,
  platform,
  eventType,
  leagueSpotIdType,
  setLeagueSpotIdType,
}: {
  competitionName: string;
  setCompetitionName: (name: string) => void;
  championshipId: string;
  setChampionshipId: (id: string) => void;
  platform: string;
  eventType: string;
  leagueSpotIdType: string;
  setLeagueSpotIdType: (type: string) => void;
}) {
  const getLeagueSpotLabel = () => {
    if (platform !== "leaguespot") return "";
    if (eventType === "event") {
      return leagueSpotIdType === "stage"
        ? "LeagueSpot Stage ID (for bracket/playoff phase)"
        : "LeagueSpot Season ID";
    }
    return "LeagueSpot Season ID";
  };

  const getLeagueSpotPlaceholder = () => {
    if (platform !== "leaguespot") return "";
    if (eventType === "event") {
      return leagueSpotIdType === "stage"
        ? "Stage ID (for bracket phase)"
        : "Season ID";
    }
    return "Season ID";
  };

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Input Data</h1>
      <div className="w-full max-w-md space-y-4">
        <div>
          <Label htmlFor="competitionName">Competition Name</Label>
          <Input
            id="competitionName"
            value={competitionName}
            onChange={(e) => setCompetitionName(e.target.value)}
            placeholder="Competition Name"
            className="max-w-xl"
          />
        </div>

        {/* Show ID type selector for LeagueSpot event imports */}
        {platform === "leaguespot" && eventType === "event" && (
          <div>
            <Label>ID Type</Label>
            <RadioGroup
              value={leagueSpotIdType}
              onValueChange={setLeagueSpotIdType}
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="season" id="season" />
                <Label htmlFor="season">Season ID (uses current stage)</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="stage" id="stage" />
                <Label htmlFor="stage">
                  Stage ID (for specific bracket/playoff phase)
                </Label>
              </div>
            </RadioGroup>
          </div>
        )}

        {platform === "regentsleague" && (
          <div>
            <Label className="mb-4">Division</Label>
            <RadioGroup
              value={championshipId}
              onValueChange={setChampionshipId}
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="Elites" id="division" />
                <Label htmlFor="division">Elites</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="Challengers" id="division" />
                <Label htmlFor="division">Challengers</Label>
              </div>
            </RadioGroup>
          </div>
        )}

        {platform !== "regentsleague" && (
          <div>
            <Label htmlFor="championshipId">
              {platform === "faceit"
                ? "Faceit Championship ID"
                : getLeagueSpotLabel()}
            </Label>
            <Input
              id="championshipId"
              value={championshipId}
              onChange={(e) => setChampionshipId(e.target.value)}
              placeholder={
                platform === "faceit"
                  ? "Faceit Championship ID"
                  : getLeagueSpotPlaceholder()
              }
              className="max-w-xl"
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ImportPreview({
  previewData,
  isLoading,
}: {
  previewData: any;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="mb-8 flex flex-col items-center justify-center space-y-4">
        <h1 className="text-3xl">Loading Preview...</h1>
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
      </div>
    );
  }

  if (!previewData) {
    return (
      <div className="mb-8 flex flex-col items-center justify-center space-y-4">
        <h1 className="text-3xl">Import Preview</h1>
        <p>No data available for preview</p>
      </div>
    );
  }

  // For Faceit data
  const matches = previewData.items || [];

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Import Preview</h1>
      <div className="w-full max-w-2xl">
        <p>Found {matches.length} matches to import</p>
        <div className="mt-4 max-h-80 overflow-y-auto rounded border p-4">
          {matches.map((match: any, index: number) => {
            const team1Key = Object.keys(match.teams)[0];
            const team2Key = Object.keys(match.teams)[1];
            const team1 = match.teams[team1Key];
            const team2 = match.teams[team2Key];

            return (
              <div key={match.match_id || index} className="mb-2 border-b p-2">
                <p className="font-semibold">
                  {team1?.name || "Team 1"} vs {team2?.name || "Team 2"}
                </p>
                <p className="text-sm">Status: {match.status}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Roster overlap at which a suggestion is pre-selected instead of "create new"
const AUTO_SELECT_MIN_OVERLAP = 2;

function suggestionReason(
  suggestion: ResolvedImportTeam["suggestions"][number],
  rosterSize: number,
) {
  if (suggestion.roster_overlap > 0) {
    return `${suggestion.roster_overlap}/${rosterSize} players already on this team`;
  }
  return `Name ${Math.round(suggestion.name_score * 100)}% similar`;
}

function UnmatchedTeamCard({
  team,
  allTeams,
  choice,
  onChoose,
}: {
  team: ResolvedImportTeam;
  allTeams: Team[];
  choice: string | undefined;
  onChoose: (teamId: string | undefined) => void;
}) {
  const [search, setSearch] = useState("");
  // Teams the platform gives no ID for can't be linked before import
  const linkable = !team.key.startsWith("name:");

  const query = search.trim().toLowerCase();
  const searchResults = query
    ? allTeams
        .filter((t) => t.name.toLowerCase().includes(query))
        .slice(0, 8)
    : [];
  const chosenFromSearch =
    choice && !team.suggestions.some((s) => s.team.id === choice)
      ? allTeams.find((t) => t.id === choice)
      : undefined;

  const optionClass = (selected: boolean) =>
    `hover:bg-muted/50 flex cursor-pointer items-center justify-between border-b p-2 ${selected ? "bg-muted" : ""}`;

  return (
    <div className="rounded-md border p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-lg font-semibold">{team.name}</h3>
        <span className="text-sm text-gray-600">
          {team.roster_size} player{team.roster_size === 1 ? "" : "s"}
        </span>
      </div>

      {team.ambiguous && (
        <p className="mb-2 text-sm text-red-600">
          Several existing teams are named "{team.name}". Pick one, or the
          import will fail.
        </p>
      )}

      {!linkable ? (
        <p className="text-sm text-gray-600">
          The platform gives no ID for this team, so it can't be linked before
          import. A new team will be created; merge it afterwards if needed.
        </p>
      ) : (
        <>
          {team.suggestions.map((suggestion) => (
            <div
              key={suggestion.team.id}
              className={optionClass(choice === suggestion.team.id)}
              onClick={() => onChoose(suggestion.team.id)}
            >
              <div>
                <p className="font-semibold">{suggestion.team.name}</p>
                <p className="text-sm text-gray-600">
                  {suggestionReason(suggestion, team.roster_size)}
                </p>
              </div>
              <span className="text-sm text-gray-600">
                {suggestion.team.elo} Elo
              </span>
            </div>
          ))}

          {chosenFromSearch && (
            <div className={optionClass(true)}>
              <p className="font-semibold">{chosenFromSearch.name}</p>
              <span className="text-sm text-gray-600">
                {chosenFromSearch.elo} Elo
              </span>
            </div>
          )}

          {!team.ambiguous && (
            <div
              className={optionClass(!choice)}
              onClick={() => onChoose(undefined)}
            >
              <p className="font-semibold">Create new team</p>
            </div>
          )}

          <Input
            placeholder="Search all teams..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mt-3"
          />
          {searchResults.map((result) => (
            <div
              key={result.id}
              className={optionClass(choice === result.id)}
              onClick={() => {
                onChoose(result.id);
                setSearch("");
              }}
            >
              <div>
                <p className="font-semibold">{result.name}</p>
                <p className="text-sm text-gray-600">
                  {result.school_name || "School not specified"}
                </p>
              </div>
              <span className="text-sm text-gray-600">{result.elo} Elo</span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function ParticipantMatcher({
  previewData,
  platform,
  selectedSeason,
  isLoading,
  setIsLoading,
  setParticipantMatches,
}: {
  previewData: any;
  platform: string;
  selectedSeason: string;
  competitionName: string;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  setParticipantMatches: (matches: Record<string, string>) => void;
}) {
  const [resolvedTeams, setResolvedTeams] = useState<ResolvedImportTeam[]>([]);
  const [allTeams, setAllTeams] = useState<Team[]>([]);
  const [error, setError] = useState<string>("");
  // Existing team chosen for each unmatched platform team, by team key;
  // no entry means the import creates a new team
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [showMatched, setShowMatched] = useState(false);

  useEffect(() => {
    if (!previewData) return;

    const resolveTeams = async () => {
      setIsLoading(true);
      setError("");
      try {
        // Dry run of the import's own team lookup, so only the teams it would
        // create are shown
        const [resolved, teams] = await Promise.all([
          resolveImportTeams({
            platform: platform as ImportMatchesRequest["platform"],
            season_id: selectedSeason,
            data: previewData,
          }),
          fetchAllTeams(),
        ]);
        setResolvedTeams(resolved.teams);
        setAllTeams(teams);

        // Pre-select suggestions backed by the roster
        const initialChoices: Record<string, string> = {};
        resolved.teams.forEach((team) => {
          const top = team.suggestions[0];
          if (!team.match && top?.roster_overlap >= AUTO_SELECT_MIN_OVERLAP) {
            initialChoices[team.key] = top.team.id;
          }
        });
        setChoices(initialChoices);
      } catch (err: any) {
        setError(err.response?.data?.error || "Failed to check teams");
      } finally {
        setIsLoading(false);
      }
    };

    resolveTeams();
  }, [previewData, platform, selectedSeason, setIsLoading]);

  // Keep the import's participant matches in sync with the choices
  useEffect(() => {
    const matches: Record<string, string> = {};
    Object.entries(choices).forEach(([key, teamId]) => {
      matches[`platform:${platform}:id:${key}`] = teamId;
    });
    setParticipantMatches(matches);
  }, [choices, platform, setParticipantMatches]);

  const unmatched = resolvedTeams.filter((team) => !team.match);
  const matched = resolvedTeams.filter((team) => team.match);
  const newTeamCount = unmatched.filter((team) => !choices[team.key]).length;

  const choose = (key: string, teamId: string | undefined) => {
    setChoices((prev) => {
      const next = { ...prev };
      if (teamId) {
        next[key] = teamId;
      } else {
        delete next[key];
      }
      return next;
    });
  };

  return (
    <div className="mb-8 flex flex-col items-center justify-center space-y-4">
      <h1 className="text-3xl">Participant Matcher</h1>

      {isLoading ? (
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : (
        <div className="w-full space-y-4">
          {unmatched.length === 0 ? (
            <Alert variant="default">
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>All teams matched</AlertTitle>
              <AlertDescription>
                All {resolvedTeams.length} teams link to existing teams.
              </AlertDescription>
            </Alert>
          ) : (
            <>
              <p className="text-center text-gray-600">
                {matched.length} of {resolvedTeams.length} teams link to
                existing teams. Review the {unmatched.length} below; the import
                will create {newTeamCount} new team
                {newTeamCount === 1 ? "" : "s"}.
              </p>
              {unmatched.map((team) => (
                <UnmatchedTeamCard
                  key={team.key}
                  team={team}
                  allTeams={allTeams}
                  choice={choices[team.key]}
                  onChoose={(teamId) => choose(team.key, teamId)}
                />
              ))}
            </>
          )}

          {matched.length > 0 && (
            <div className="rounded-md border p-4">
              <button
                className="w-full cursor-pointer text-left font-semibold"
                onClick={() => setShowMatched((prev) => !prev)}
              >
                {showMatched ? "Hide" : "Show"} {matched.length} matched team
                {matched.length === 1 ? "" : "s"}
              </button>
              {showMatched && (
                <table className="mt-2 w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="p-2 text-left">Platform Team</th>
                      <th className="p-2 text-left">Existing Team</th>
                      <th className="p-2 text-right">Matched By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matched.map((team) => (
                      <tr key={team.key} className="border-b">
                        <td className="p-2">{team.name}</td>
                        <td className="p-2">
                          {team.match!.team.name} ({team.match!.team.elo})
                        </td>
                        <td className="p-2 text-right text-sm text-gray-600">
                          {team.match!.method === "platform_id"
                            ? "Platform ID"
                            : "Name"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ImportMatches() {
  // State for multi-step form
  const [step, setStep] = useState(0);
  const [platform, setPlatform] = useState("faceit");
  const [eventType, setEventType] = useState("event");
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [events, setEvents] = useState<PublicEvent[]>([]);
  const [selectedSeason, setSelectedSeason] = useState("");
  const [showCreateSeason, setShowCreateSeason] = useState(false);
  const [showCreateEvent, setShowCreateEvent] = useState(false);
  const [eventId, setEventId] = useState("");
  const [eventName, setEventName] = useState("");
  const [competitionName, setCompetitionName] = useState("");
  const [championshipId, setChampionshipId] = useState(""); // Faceit/Leaguespot ID
  const [leagueSpotIdType, setLeagueSpotIdType] = useState("season"); // "season" or "stage"
  const [previewData, setPreviewData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [importStatus, setImportStatus] = useState<{
    success?: boolean;
    message?: string;
    details?: {
      new: number;
      updated: number;
      skipped: number;
    };
  }>({});
  const [participantMatches, setParticipantMatches] = useState<
    Record<string, string>
  >({});

  // Fetch seasons on component mount
  useEffect(() => {
    const getSeasons = async () => {
      try {
        const seasonsData = await fetchSeasons();
        setSeasons(seasonsData);
        if (seasonsData.length > 0) {
          setSelectedSeason(seasonsData[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch seasons:", error);
      }
    };

    getSeasons();
  }, []);

  // Fetch events when season is selected (for event type)
  useEffect(() => {
    if (selectedSeason && eventType === "event") {
      const getEvents = async () => {
        try {
          const eventsData = await fetchAllEvents();
          // Filter events by selected season if needed
          const filteredEvents = eventsData.filter(
            (event) => !event.season || event.season.id === selectedSeason,
          );
          setEvents(filteredEvents);
        } catch (error) {
          console.error("Failed to fetch events:", error);
        }
      };

      getEvents();
    }
  }, [selectedSeason, eventType]);

  const handleNewSeason = (newSeason: Season) => {
    setSeasons([...seasons, newSeason]);
    setSelectedSeason(newSeason.id);
    setShowCreateSeason(false);
  };

  const handleNewEvent = (newEventId: string, newEventName: string) => {
    setEventId(newEventId);
    setEventName(newEventName);
    setShowCreateEvent(false);

    // Refresh events list
    const refreshEvents = async () => {
      try {
        const eventsData = await fetchAllEvents();
        const filteredEvents = eventsData.filter(
          (event) => !event.season || event.season.id === selectedSeason,
        );
        setEvents(filteredEvents);
      } catch (error) {
        console.error("Failed to refresh events:", error);
      }
    };
    refreshEvents();
  };

  const handleSelectEvent = (eventId: string, eventName: string) => {
    setEventId(eventId);
    setEventName(eventName);
  };

  const nextStep = async () => {
    // Validate current step
    if (step === 2 && !selectedSeason) {
      alert("Please select a season");
      return;
    }

    // For event type, validate event is created/selected (step 3)
    if (eventType === "event" && step === 3 && !eventId) {
      alert("Please create an event");
      return;
    }

    // For both types, validate championship ID (step 4 for events, step 3 for leagues)
    const metadataStep = eventType === "event" ? 4 : 3;
    if (step === metadataStep && (!competitionName || !championshipId)) {
      alert("Please fill in all fields");
      return;
    }

    // Special handling for preview step
    const previewStep = eventType === "event" ? 5 : 4;
    if (step === previewStep) {
      setIsLoading(true);
      try {
        let data;
        if (platform === "faceit") {
          data = await fetchFaceitMatches(championshipId);
          // Filter out matches with unknown teams for Faceit as well
          if (data && data.items) {
            const originalCount = data.items.length;
            data.items = data.items.filter((match: any) => {
              const teams = match.teams || {};
              const teamNames = Object.values(teams).map((team: any) =>
                (team.name || "").toLowerCase(),
              );

              const hasUnknownTeam = teamNames.some(
                (name) =>
                  name === "unknown team 1" ||
                  name === "unknown team 2" ||
                  name === "tbd" ||
                  name === "bye",
              );

              if (hasUnknownTeam) {
                console.log(
                  `Skipping Faceit match ${match.match_id} with unknown/TBD teams`,
                );
                return false;
              }
              return true;
            });
            console.log(
              `Filtered Faceit matches: ${originalCount} → ${data.items.length}`,
            );
          }
        } else if (platform === "regentsleague") {
          data = await fetchRegentsLeagueMatches(championshipId);
        } else {
          // Use LeagueSpot API for Playfly matches
          // For events, use the selected ID type (season or stage)
          // For leagues, always use season
          const idType =
            eventType === "event"
              ? (leagueSpotIdType as "season" | "stage")
              : "season";
          data = await fetchPlayflyMatchesViaLeagueSpot(championshipId, idType);
          // LeagueSpot filtering is already done in convertLeagueSpotDataToSchema
        }
        setPreviewData(data);
      } catch (error) {
        console.error("Failed to fetch preview data:", error);
        alert(
          "Failed to fetch preview data. Please check the season/stage ID and try again.",
        );
        setIsLoading(false);
        return;
      }
      setIsLoading(false);
    }

    // Special handling for import step (now moved to after participant matching)
    const importStep = eventType === "event" ? 6 : 5;
    if (step === importStep) {
      setIsLoading(true);
      try {
        // Include participant matches in the import request
        const result = await importMatches({
          platform: platform as "faceit" | "leaguespot" | "regentsleague",
          competition_name: competitionName,
          season_id: selectedSeason,
          data: previewData,
          participant_matches: participantMatches,
          event_id: eventType === "event" ? eventId : undefined,
          import_type: eventType as "league" | "event",
        });

        // Build detailed message
        const messageParts = [];
        if (result.matches_imported > 0) {
          messageParts.push(`${result.matches_imported} new`);
        }
        if (result.matches_updated > 0) {
          messageParts.push(`${result.matches_updated} updated`);
        }
        if (result.matches_skipped > 0) {
          messageParts.push(`${result.matches_skipped} unchanged`);
        }

        const detailedMessage =
          messageParts.length > 0
            ? `Import complete: ${messageParts.join(", ")} match(es)`
            : "No new matches to import";

        setImportStatus({
          success: true,
          message: detailedMessage,
          details: {
            new: result.matches_imported,
            updated: result.matches_updated,
            skipped: result.matches_skipped,
          },
        });
      } catch (error: any) {
        console.error("Import failed:", error);
        setImportStatus({
          success: false,
          message:
            error.response?.data?.error || "Import failed. Please try again.",
        });
      }
      setIsLoading(false);
    }

    setStep((prev) => Math.min(prev + 1, eventType === "event" ? 7 : 6));
  };

  const prevStep = () => {
    setStep((prev) => Math.max(prev - 1, 0));
  };

  // Render current step
  const renderStep = () => {
    if (showCreateSeason) {
      return (
        <CreateSeasonForm
          onCancel={() => setShowCreateSeason(false)}
          onSuccess={handleNewSeason}
        />
      );
    }

    if (showCreateEvent) {
      return (
        <CreateEventForm
          onCancel={() => setShowCreateEvent(false)}
          onSuccess={handleNewEvent}
          selectedSeason={selectedSeason}
        />
      );
    }

    switch (step) {
      case 0:
        return <SelectPlatform platform={platform} setPlatform={setPlatform} />;
      case 1:
        return (
          <SelectLeagueOrEvent
            eventType={eventType}
            setEventType={setEventType}
          />
        );
      case 2:
        return (
          <SelectOrCreateSeason
            seasons={seasons}
            selectedSeason={selectedSeason}
            setSelectedSeason={setSelectedSeason}
            setShowCreateSeason={setShowCreateSeason}
          />
        );
      case 3:
        // For event type, show event selection/creation; for league, show metadata
        if (eventType === "event") {
          return eventId ? (
            <div className="mb-8 flex flex-col items-center justify-center space-y-4">
              <h1 className="text-3xl">Selected Event</h1>
              <div className="w-full max-w-md space-y-4">
                <Alert variant="default">
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertTitle>Event Selected</AlertTitle>
                  <AlertDescription>
                    Event "{eventName}" has been selected.
                  </AlertDescription>
                </Alert>
                <Button
                  variant="outline"
                  onClick={() => {
                    setEventId("");
                    setEventName("");
                  }}
                  className="w-full"
                >
                  Select Different Event
                </Button>
              </div>
            </div>
          ) : (
            <SelectOrCreateEvent
              events={events}
              selectedEvent={eventId}
              setSelectedEvent={handleSelectEvent}
              setShowCreateEvent={setShowCreateEvent}
            />
          );
        } else {
          return (
            <MetadataForm
              competitionName={competitionName}
              setCompetitionName={setCompetitionName}
              championshipId={championshipId}
              setChampionshipId={setChampionshipId}
              platform={platform}
              eventType={eventType}
              leagueSpotIdType={leagueSpotIdType}
              setLeagueSpotIdType={setLeagueSpotIdType}
            />
          );
        }
      case 4:
        // For event type, show metadata form; for league, show preview
        if (eventType === "event") {
          return (
            <MetadataForm
              competitionName={competitionName}
              setCompetitionName={setCompetitionName}
              championshipId={championshipId}
              setChampionshipId={setChampionshipId}
              platform={platform}
              eventType={eventType}
              leagueSpotIdType={leagueSpotIdType}
              setLeagueSpotIdType={setLeagueSpotIdType}
            />
          );
        } else {
          return (
            <ImportPreview previewData={previewData} isLoading={isLoading} />
          );
        }
      case 5:
        // For event type, show preview; for league, show participant matcher
        if (eventType === "event") {
          return (
            <ImportPreview previewData={previewData} isLoading={isLoading} />
          );
        } else {
          return (
            <ParticipantMatcher
              previewData={previewData}
              platform={platform}
              selectedSeason={selectedSeason}
              competitionName={competitionName}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              setParticipantMatches={setParticipantMatches}
            />
          );
        }
      case 6:
        // For event type, show participant matcher; for league, show complete
        if (eventType === "event") {
          return (
            <ParticipantMatcher
              previewData={previewData}
              platform={platform}
              selectedSeason={selectedSeason}
              competitionName={competitionName}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
              setParticipantMatches={setParticipantMatches}
            />
          );
        } else {
          return (
            <div className="mb-8 flex flex-col items-center justify-center space-y-4">
              <h1 className="text-3xl">Import Complete</h1>
              {importStatus.success ? (
                <Alert variant="default" className="mb-4">
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertTitle>Success</AlertTitle>
                  <AlertDescription>{importStatus.message}</AlertDescription>
                </Alert>
              ) : (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>
                    {importStatus.message || "An error occurred during import."}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          );
        }
      case 7:
        // Event type complete step
        return (
          <div className="mb-8 flex flex-col items-center justify-center space-y-4">
            <h1 className="text-3xl">Import Complete</h1>
            {importStatus.success ? (
              <>
                <Alert variant="default" className="mb-4 w-full max-w-md">
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertTitle>Success</AlertTitle>
                  <AlertDescription>
                    {importStatus.message}
                    {importStatus.details && (
                      <div className="mt-2 text-sm">
                        <ul className="list-inside list-disc space-y-1">
                          {importStatus.details.new > 0 && (
                            <li>
                              {importStatus.details.new} new match(es) imported
                            </li>
                          )}
                          {importStatus.details.updated > 0 && (
                            <li>
                              {importStatus.details.updated} existing match(es)
                              updated
                            </li>
                          )}
                          {importStatus.details.skipped > 0 && (
                            <li>
                              {importStatus.details.skipped} match(es) unchanged
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                  </AlertDescription>
                </Alert>

                {/* Re-import option for events */}
                <div className="w-full max-w-md space-y-4">
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Re-import Event Matches</AlertTitle>
                    <AlertDescription>
                      As the event progresses and new rounds are scheduled, you
                      can re-import to add newly scheduled matches or update
                      existing ones.
                    </AlertDescription>
                  </Alert>

                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        // Reset to championship ID step but keep event and season
                        setStep(4);
                        setPreviewData(null);
                        setParticipantMatches({});
                        setImportStatus({});
                      }}
                      className="flex-1"
                    >
                      Re-import Event
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        // Full reset
                        window.location.reload();
                      }}
                      className="flex-1"
                    >
                      Start New Import
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>
                  {importStatus.message || "An error occurred during import."}
                </AlertDescription>
              </Alert>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex justify-center">
      <div className="w-full max-w-[600px]">
        <h1 className="mb-8 text-2xl font-bold">Import Matches</h1>

        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex justify-between">
            {eventType === "event"
              ? [
                  "Platform",
                  "Type",
                  "Season",
                  "Event",
                  "Details",
                  "Preview",
                  "Match",
                  "Complete",
                ].map((label, index) => (
                  <div
                    key={label}
                    className={`flex flex-col items-center ${index <= step ? "text-primary" : "text-muted-foreground"}`}
                  >
                    <div
                      className={`mb-1 flex h-6 w-6 items-center justify-center rounded-full ${
                        index < step
                          ? "bg-primary text-white"
                          : index === step
                            ? "border-primary border-2"
                            : "border-muted border-2"
                      }`}
                    >
                      {index < step ? "✓" : ""}
                    </div>
                    <span className="text-xs">{label}</span>
                  </div>
                ))
              : [
                  "Platform",
                  "Type",
                  "Season",
                  "Details",
                  "Preview",
                  "Match",
                  "Complete",
                ].map((label, index) => (
                  <div
                    key={label}
                    className={`flex flex-col items-center ${index <= step ? "text-primary" : "text-muted-foreground"}`}
                  >
                    <div
                      className={`mb-1 flex h-6 w-6 items-center justify-center rounded-full ${
                        index < step
                          ? "bg-primary text-white"
                          : index === step
                            ? "border-primary border-2"
                            : "border-muted border-2"
                      }`}
                    >
                      {index < step ? "✓" : ""}
                    </div>
                    <span className="text-xs">{label}</span>
                  </div>
                ))}
          </div>
          <div className="bg-muted mt-2 h-1">
            <div
              className="bg-primary h-full transition-all"
              style={{
                width: `${(step / (eventType === "event" ? 7 : 6)) * 100}%`,
              }}
            ></div>
          </div>
        </div>

        {importStatus.message && (
          <Alert
            variant={importStatus.success ? "default" : "destructive"}
            className="mb-4"
          >
            {importStatus.success ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <AlertTitle>
              {importStatus.success ? "Success" : "Error"}
            </AlertTitle>
            <AlertDescription>{importStatus.message}</AlertDescription>
          </Alert>
        )}

        {renderStep()}

        <div className="mt-8 flex justify-between">
          {step > 0 && (
            <button
              className="cursor-pointer rounded-md bg-gray-300 p-2 px-4 text-gray-800 transition-all duration-300 hover:bg-gray-400"
              onClick={prevStep}
              disabled={isLoading}
            >
              Previous
            </button>
          )}
          <div className="flex-1"></div>
          <button
            className="bg-primary cursor-pointer rounded-md p-2 px-4 text-white transition-all duration-300 hover:bg-[#b5670b]"
            onClick={nextStep}
            disabled={isLoading}
          >
            {isLoading
              ? "Loading..."
              : step === (eventType === "event" ? 6 : 5)
                ? "Import"
                : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ImportMatches;
