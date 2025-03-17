import { Container, ListGroup, Badge, Spinner, Alert } from "react-bootstrap";
import { Player, Team } from "../../types";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import logo from "../../assets/0.5x/C Logo@0.5x.png";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

interface SearchResults {
  players: Player[];
  teams: Team[];
}

const fetchSearchResults = async (
  searchQuery: string
): Promise<SearchResults> => {
  if (!searchQuery || searchQuery === "") return { players: [], teams: [] };
  const response = await fetch(`${apiBaseUrl}/search/${searchQuery}`);
  return response.json();
};

const Search = () => {
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get("query") || "";

  const {
    data: searchResults,
    isPending: searchLoading,
    isError: searchError,
    error: searchErrorObj,
  } = useQuery({
    queryKey: ["search", searchQuery],
    queryFn: () => fetchSearchResults(searchQuery || ""),
    staleTime: 1000 * 60 * 10,
  });

  if (searchLoading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <Spinner animation="border" />
      </div>
    );
  }

  if (searchError) {
    return (
      <Alert variant="danger">
        {" "}
        <strong>Error: </strong>
        {searchErrorObj?.message}
      </Alert>
    );
  }
  return (
    <Container style={{ maxWidth: "800px" }}>
      <h1>Search Results</h1>
      <ListGroup style={{ marginBottom: "10px", padding: "20px" }}>
        <ListGroup.Item>
          <h1>Teams</h1>
        </ListGroup.Item>
        {searchResults?.teams && searchResults.teams.length > 0 ? (
          searchResults.teams.map((team) => (
            <ListGroup.Item key={team.team_id}>
              <img
                src={team.avatar ? team.avatar : logo}
                alt={`logo`}
                style={{
                  height: "40px",
                  borderRadius: "5px",
                  backgroundColor: "white",
                  marginRight: "10px",
                }}
              />
              <Link to={`/team?id=${team.team_id}`}>{team.name}</Link>
            </ListGroup.Item>
          ))
        ) : (
          <ListGroup.Item style={{ fontStyle: "italic" }}>
            No teams found
          </ListGroup.Item>
        )}
      </ListGroup>
      <ListGroup style={{ marginBottom: "20px", padding: "20px" }}>
        <ListGroup.Item>
          <h1>Players</h1>
        </ListGroup.Item>
        {searchResults?.players && searchResults.players.length > 0 ? (
          searchResults?.players.map((player) => (
            <ListGroup.Item key={player.player_id}>
              <Link to={`/player?id=${player.player_id}`}>
                {player.nickname}
              </Link>
              <Badge bg="secondary" style={{ marginLeft: "1rem" }}>
                Level: {player.skill_level}
              </Badge>
            </ListGroup.Item>
          ))
        ) : (
          <ListGroup.Item style={{ fontStyle: "italic" }}>
            No players found
          </ListGroup.Item>
        )}
      </ListGroup>
    </Container>
  );
};

export default Search;
