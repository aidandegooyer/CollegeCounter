import React, { useEffect, useState } from "react";
import { Container, Form, Button, Image } from "react-bootstrap";
import { Player, Team } from "../../../types";

const UserPicture: React.FC = () => {
  const [Teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [privateKey, setPrivateKey] = useState<string | null>(null);

  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleSecretKeyChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const key = event.target.value;
    setPrivateKey(key);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedFile && selectedPlayer) {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("player_id", selectedPlayer.player_id);

      fetch(`${apiBaseUrl}/upload_profile_pic?token=${privateKey}`, {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Success:", data);
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    }
  };

  const fetchTeams = async () => {
    const response = await fetch(`${apiBaseUrl}/teams`);
    const teams: Team[] = await response.json();
    setTeams(teams);
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  return (
    <Container style={{ maxWidth: "600px", padding: "0 1rem" }}>
      <h1>Replace User Profile Picture</h1>
      <Form onSubmit={handleSubmit}>
        <Form.Group controlId="formFile" className="mb-3">
          <Form.Label>Select Team</Form.Label>
          <Form.Control
            as="select"
            value={selectedTeam?.team_id || ""}
            onChange={async (e) => {
              const teamId = e.target.value;
              const team = Teams.find((t) => t.team_id === teamId) || null;
              setSelectedTeam(team);
              if (team) {
                const response = await fetch(
                  `${apiBaseUrl}/team/${teamId}/players`
                );
                const players: Player[] = await response.json();
                setPlayers(players);
              }
            }}
          >
            <option value="" disabled>
              Select a team
            </option>
            {Teams.map((team) => (
              <option key={team.team_id} value={team.team_id}>
                {team.name}
              </option>
            ))}
          </Form.Control>
          {selectedTeam && (
            <>
              <Form.Label>Select Player</Form.Label>
              <Form.Control
                as="select"
                value={selectedPlayer?.player_id || ""}
                onChange={(e) => {
                  const playerId = e.target.value;
                  const player =
                    players.find((p) => p.player_id === playerId) || null;
                  setSelectedPlayer(player);
                }}
              >
                <option value="" disabled>
                  Select a player
                </option>
                {players.map((player) => (
                  <option key={player.player_id} value={player.player_id}>
                    {player.nickname}
                  </option>
                ))}
              </Form.Control>
            </>
          )}
          <Form.Label>Upload new profile picture</Form.Label>
          <Form.Control type="file" onChange={handleFileChange} />
          <Form.Label>enter private key</Form.Label>
          <Form.Control type="text" onChange={handleSecretKeyChange} />
        </Form.Group>
        {preview && <Image src={preview} thumbnail />}

        <Button variant="primary" type="submit">
          Submit
        </Button>
      </Form>
    </Container>
  );
};

export default UserPicture;
