import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import {
  fetchAllTeams,
  fetchAllPlayers,
  fetchAllMatches,
} from "@/services/api";
import type { Team, Player, Match } from "@/services/api";

function DatabaseViewer() {
  const [activeTab, setActiveTab] = useState("teams");
  const [teams, setTeams] = useState([] as Team[]);
  const [players, setPlayers] = useState([] as Player[]);
  const [matches, setMatches] = useState([] as Match[]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // This will be replaced with actual API calls once they're available
        // For now, we're using mock data
        switch (activeTab) {
          case "teams":
            const teamsData = await fetchAllTeams();
            setTeams(teamsData);

            break;
          case "players":
            const playersData = await fetchAllPlayers();
            setPlayers(playersData);
            break;
          case "matches":
            const matchesData = await fetchAllMatches();
            setMatches(matchesData);
            break;
        }
      } catch (err) {
        setError("Failed to fetch data. Please try again.");
        console.error("Error fetching data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [activeTab]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const filteredTeams = teams.filter(
    (team) =>
      team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (team.school_name &&
        team.school_name.toLowerCase().includes(searchTerm.toLowerCase())),
  );

  const filteredPlayers = players.filter((player) =>
    player.name.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const filteredMatches = matches.filter(
    (match) =>
      match.team1?.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      match.team2?.name.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Database Viewer</h2>

      <div className="flex items-center space-x-2">
        <Search className="h-5 w-5 text-gray-400" />
        <Input
          placeholder="Search..."
          value={searchTerm}
          onChange={handleSearch}
          className="max-w-sm"
        />
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="teams">Teams</TabsTrigger>
          <TabsTrigger value="players">Players</TabsTrigger>
          <TabsTrigger value="matches">Matches</TabsTrigger>
        </TabsList>

        <TabsContent value="teams">
          {loading ? (
            <div className="py-8 text-center">Loading teams...</div>
          ) : error ? (
            <div className="py-8 text-center text-red-500">{error}</div>
          ) : (
            <Table>
              <TableCaption>List of teams in the database</TableCaption>
              <TableHeader>
                <TableRow className="bg-muted">
                  <TableHead>Name</TableHead>
                  <TableHead>School</TableHead>
                  <TableHead>ELO</TableHead>
                  <TableHead>Captain</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTeams.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center">
                      No teams found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTeams.map((team) => (
                    <TableRow key={team.id}>
                      <TableCell>{team.name}</TableCell>
                      <TableCell>{team.school_name || "N/A"}</TableCell>
                      <TableCell>{team.elo}</TableCell>
                      <TableCell>{team.captain?.name || "N/A"}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
              <TableFooter>
                <TableRow className="bg-muted">
                  <TableHead>TOTAL</TableHead>
                  <TableHead></TableHead>
                  <TableHead></TableHead>
                  <TableHead>{filteredTeams.length}</TableHead>
                </TableRow>
              </TableFooter>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="players">
          {loading ? (
            <div className="py-8 text-center">Loading players...</div>
          ) : error ? (
            <div className="py-8 text-center text-red-500">{error}</div>
          ) : (
            <Table>
              <TableCaption>List of players in the database</TableCaption>
              <TableHeader>
                <TableRow className="bg-muted">
                  <TableHead>Name</TableHead>
                  <TableHead>Team</TableHead>
                  <TableHead>ELO</TableHead>
                  <TableHead>Skill Level</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPlayers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center">
                      No players found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredPlayers.map((player) => (
                    <TableRow key={player.id}>
                      <TableCell>{player.name}</TableCell>
                      <TableCell>{player.team?.name || "N/A"}</TableCell>
                      <TableCell>{player.elo}</TableCell>
                      <TableCell>{player.skill_level}</TableCell>
                      <TableCell>
                        {player.benched ? "Benched" : "Active"}
                        {!player.visible ? " (Hidden)" : ""}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
              <TableFooter>
                <TableRow className="bg-muted">
                  <TableHead>TOTAL</TableHead>
                  <TableHead></TableHead>
                  <TableHead></TableHead>
                  <TableHead></TableHead>
                  <TableHead>{filteredPlayers.length}</TableHead>
                </TableRow>
              </TableFooter>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="matches">
          {loading ? (
            <div className="py-8 text-center">Loading matches...</div>
          ) : error ? (
            <div className="py-8 text-center text-red-500">{error}</div>
          ) : (
            <Table>
              <TableCaption>List of matches in the database</TableCaption>
              <TableHeader>
                <TableRow className="bg-muted">
                  <TableHead>Teams</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Platform</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMatches.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center">
                      No matches found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMatches.map((match) => (
                    <TableRow key={match.id}>
                      <TableCell>
                        {match.team1.name} vs {match.team2.name}
                      </TableCell>
                      <TableCell>
                        {match.score_team1} - {match.score_team2}
                      </TableCell>
                      <TableCell>
                        {new Date(match.date).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {match.status.charAt(0).toUpperCase() +
                          match.status.slice(1)}
                      </TableCell>
                      <TableCell>{match.platform}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
              <TableFooter>
                <TableRow className="bg-muted">
                  <TableHead>TOTAL</TableHead>
                  <TableHead></TableHead>
                  <TableHead></TableHead>
                  <TableHead></TableHead>
                  <TableHead>{filteredMatches.length}</TableHead>
                </TableRow>
              </TableFooter>
            </Table>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default DatabaseViewer;
