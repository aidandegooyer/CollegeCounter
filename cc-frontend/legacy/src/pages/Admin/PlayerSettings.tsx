import React, { useEffect, useState } from "react";
import { Container, Form, Button, Image, FormGroup } from "react-bootstrap";
import { Player, Team } from "../../types";

const PlayerSettings: React.FC = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [playerDetails, setPlayerDetails] = useState<Player | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [privateKey, setPrivateKey] = useState<string>("");

  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

  // Fetch teams when component mounts.
  useEffect(() => {
    fetch(`${apiBaseUrl}/teams`)
      .then((response) => response.json())
      .then((data: Team[]) => setTeams(data))
      .catch((error) => console.error("Error fetching teams:", error));
  }, [apiBaseUrl]);

  // When a team is selected, fetch players for that team.
  const handleTeamSelect = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const teamId = e.target.value;
    const team = teams.find((t) => t.team_id === teamId) || null;
    setSelectedTeam(team);
    setSelectedPlayer(null);
    setPlayerDetails(null);
    if (team) {
      try {
        const response = await fetch(`${apiBaseUrl}/team/${teamId}/players`);
        const data: Player[] = await response.json();
        setPlayers(data);
      } catch (error) {
        console.error("Error fetching players:", error);
      }
    }
  };

  // When a player is selected, fetch its full details.
  const handlePlayerSelect = async (
    e: React.ChangeEvent<HTMLSelectElement>
  ) => {
    const playerId = e.target.value;
    if (playerId === "__ADD") {
      //TODO: IMPLEMENT NEW PLAYER ADDITIONS TO TEAMS. maybe paste faceit link or smth
      console.log("Add Player Selected");
      const newPlayer: Player = {
        player_id: "null", // No ID yet since it's a new player
        nickname: "New Player",
        avatar: "",
        skill_level: 1, // Default skill level
        elo: -1, // Default ELO, adjust as needed
        steam_id: "",
        faceit_id: "",
        visible: true, // Default to visible
        bench: false, // Default to not benched
      };
      setSelectedPlayer(newPlayer);
      setPlayerDetails(newPlayer);
      return;
    }
    const player = players.find((p) => p.player_id === playerId) || null;
    setSelectedPlayer(player);
    if (player) {
      try {
        const response = await fetch(`${apiBaseUrl}/player/${playerId}`);
        const data: Player = await response.json();
        setPlayerDetails(data);
      } catch (error) {
        console.error("Error fetching player details:", error);
      }
    } else {
      setPlayerDetails(null);
    }
  };

  // Handle file selection for a new avatar.
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  // Handle private key changes.
  const handleSecretKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPrivateKey(e.target.value);
  };

  // Handle changes for text, number, or checkbox inputs.
  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    if (!playerDetails) return;
    const { name, value, type, checked } = e.target as HTMLInputElement;
    setPlayerDetails({
      ...playerDetails,
      [name]:
        type === "checkbox"
          ? checked
          : type === "number"
          ? Number(value)
          : value,
    });
  };

  // Submit the updated player details.
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedPlayer || !playerDetails) return;

    const formData = new FormData();
    formData.append("nickname", playerDetails.nickname);
    formData.append("skill_level", playerDetails.skill_level.toString());
    formData.append("elo", playerDetails.elo.toString());
    if (playerDetails.steam_id)
      formData.append("steam_id", playerDetails.steam_id);
    if (playerDetails.faceit_id)
      formData.append("faceit_id", playerDetails.faceit_id);
    // Append visibility as "1" for true or "0" for false.
    formData.append("visible", playerDetails.visible ? "1" : "0");
    formData.append("bench", playerDetails.bench ? "1" : "0");
    formData.append("player_id", playerDetails.player_id);

    try {
      const response = await fetch(
        `${apiBaseUrl}/player/${selectedPlayer.player_id}?token=${privateKey}`,
        {
          method: "PUT",
          body: formData,
        }
      );
      const data = await response.json();
      alert("Player updated:" + data.toString());

      if (selectedFile) {
        const avatarFormData = new FormData();
        avatarFormData.append("file", selectedFile);
        avatarFormData.append("player_id", playerDetails.player_id);
        const avatarResponse = await fetch(`${apiBaseUrl}/upload_profile_pic`, {
          method: "POST",
          body: avatarFormData,
        });
        const avatarData = await avatarResponse.json();
        alert("Avatar updated:" + avatarData.toString());
      }
    } catch (error) {
      alert("Error updating player:" + error);
    }
  };

  async function handleNewPlayer() {
    try {
      const response = await fetch(
        `${apiBaseUrl}/add_player/${selectedTeam?.team_id}/${playerDetails?.nickname}?token=${privateKey}`
      );
      const data = await response.json();
      alert("Player added:" + data.toString());
    } catch (error) {
      alert("Error updating player:" + error);
    }
  }

  return (
    <Container style={{ maxWidth: "600px", padding: "0 1rem" }}>
      <h1>Edit Player Details</h1>
      <Form onSubmit={handleSubmit}>
        <Form.Group controlId="selectTeam" className="mb-3">
          <Form.Label>Select Team</Form.Label>
          <Form.Control
            as="select"
            value={selectedTeam?.team_id || ""}
            onChange={(e) =>
              handleTeamSelect(
                e as unknown as React.ChangeEvent<HTMLSelectElement>
              )
            }
          >
            <option value="" disabled>
              Select a team
            </option>
            {teams
              .sort((a, b) => a.name.localeCompare(b.name))
              .map((team) => (
                <option key={team.team_id} value={team.team_id}>
                  {team.name}
                </option>
              ))}
          </Form.Control>
        </Form.Group>

        {selectedTeam && (
          <Form.Group controlId="selectPlayer" className="mb-3">
            <Form.Label>Select Player</Form.Label>
            <Form.Control
              as="select"
              value={selectedPlayer?.player_id || ""}
              onChange={(e) =>
                handlePlayerSelect(
                  e as unknown as React.ChangeEvent<HTMLSelectElement>
                )
              }
            >
              <option value="" disabled>
                Select a player
              </option>
              <option value="__ADD">Add New Player...</option>
              {players.map((player) => (
                <option key={player.player_id} value={player.player_id}>
                  {player.nickname}
                </option>
              ))}
            </Form.Control>
          </Form.Group>
        )}

        {playerDetails?.player_id != "null" && playerDetails && (
          <>
            <Form.Group controlId="playerId" className="mb-3">
              <Form.Label>Player ID (cannot be edited)</Form.Label>
              <Form.Control
                type="text"
                value={playerDetails.player_id}
                disabled
              />
            </Form.Group>
            <Form.Group controlId="nickname" className="mb-3">
              <Form.Label>Nickname</Form.Label>
              <Form.Control
                type="text"
                name="nickname"
                value={playerDetails.nickname}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="skill_level" className="mb-3">
              <Form.Label>Skill Level</Form.Label>
              <Form.Control
                type="number"
                name="skill_level"
                value={playerDetails.skill_level}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="elo" className="mb-3">
              <Form.Label>ELO</Form.Label>
              <Form.Control
                type="number"
                name="elo"
                value={playerDetails.elo}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="steam_id" className="mb-3">
              <Form.Label>Steam ID</Form.Label>
              <Form.Control
                type="text"
                name="steam_id"
                value={playerDetails.steam_id || ""}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="faceit_id" className="mb-3">
              <Form.Label>Faceit ID</Form.Label>
              <Form.Control
                type="text"
                name="faceit_id"
                value={playerDetails.faceit_id || ""}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="visible" className="mb-3">
              <Form.Check
                type="checkbox"
                name="visible"
                label="Visible"
                checked={playerDetails.visible ?? true}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="bench" className="mb-3">
              <Form.Check
                type="checkbox"
                name="bench"
                label="Benched"
                checked={playerDetails.bench ?? true}
                onChange={handleInputChange}
              />
            </Form.Group>
            <Form.Group controlId="avatar" className="mb-3">
              <Form.Label>Avatar (Upload new avatar)</Form.Label>
              <Form.Control type="file" onChange={handleFileChange} />
              {preview ? (
                <Image src={preview} thumbnail className="mt-2" />
              ) : (
                playerDetails.avatar && (
                  <Image
                    src={playerDetails.avatar}
                    thumbnail
                    className="mt-2"
                  />
                )
              )}
            </Form.Group>
          </>
        )}

        {playerDetails?.player_id === "null" && (
          <>
            <p>
              New player details will be added to the selected team. Please fill
              in the details below.
            </p>
            <FormGroup controlId="nickname" className="mb-3">
              <Form.Label>Faceit Nickname</Form.Label>
              <Form.Control
                type="text"
                name="nickname"
                value={playerDetails?.nickname}
                onChange={handleInputChange}
              />
            </FormGroup>
          </>
        )}

        <Form.Group controlId="privateKey" className="mb-3">
          <Form.Label>Enter Private Key</Form.Label>
          <Form.Control
            type="text"
            value={privateKey}
            onChange={handleSecretKeyChange}
          />
        </Form.Group>

        {playerDetails?.player_id != "null" ? (
          <Button variant="primary" type="submit">
            Update Player
          </Button>
        ) : (
          <Button variant="primary" onClick={handleNewPlayer}>
            Add Player
          </Button>
        )}
      </Form>
    </Container>
  );
};

export default PlayerSettings;
