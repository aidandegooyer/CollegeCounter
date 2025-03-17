import React, { useEffect, useState } from "react";
import { Container, Form, Button, Image } from "react-bootstrap";
import { Team } from "../../types";

const TeamEditor: React.FC = () => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [teamDetails, setTeamDetails] = useState<Team | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [privateKey, setPrivateKey] = useState<string>("");

  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

  // Fetch the list of teams when the component mounts.
  useEffect(() => {
    fetch(`${apiBaseUrl}/teams`)
      .then((response) => response.json())
      .then((data: Team[]) => setTeams(data))
      .catch((error) => console.error("Error fetching teams:", error));
  }, []);

  // When a team is selected, fetch its full details from /team/<team_id>.
  const handleTeamSelect = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const teamId = e.target.value;
    const team = teams.find((t) => t.team_id === teamId) || null;
    setSelectedTeam(team);

    if (team) {
      try {
        const response = await fetch(`${apiBaseUrl}/team/${teamId}`);
        const data: Team = await response.json();
        setTeamDetails(data);
      } catch (error) {
        console.error("Error fetching team details:", error);
      }
    } else {
      setTeamDetails(null);
    }
  };

  const handleImageUpload = (selectedPic: string) => {
    if (selectedFile && selectedTeam) {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("team_id", selectedTeam.team_id);

      fetch(
        `${apiBaseUrl}/upload_team_photo?type=${selectedPic}&token=${privateKey}`,
        {
          method: "POST",
          body: formData,
        }
      )
        .then((response) => response.json())
        .then((data) => {
          console.log("Success:", data);
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    }
  };

  // Handle changes for text and number inputs.
  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    if (!teamDetails) return;
    const { name, value } = e.target;
    setTeamDetails({
      ...teamDetails,
      [name]: name === "elo" ? Number(value) : value,
    });
  };

  // Handle file selection for avatar.
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleSecretKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPrivateKey(e.target.value);
  };

  // Submit updated team details via a PUT request.
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedTeam || !teamDetails) return;

    const formData = new FormData();
    formData.append("name", teamDetails.name);
    formData.append("leader", teamDetails.leader);
    formData.append("elo", teamDetails.elo.toString());
    if (teamDetails.playfly_id)
      formData.append("playfly_id", teamDetails.playfly_id);
    if (teamDetails.playfly_participant_id)
      formData.append(
        "playfly_participant_id",
        teamDetails.playfly_participant_id
      );
    if (teamDetails.faceit_id)
      formData.append("faceit_id", teamDetails.faceit_id);
    if (teamDetails.school_name)
      formData.append("school_name", teamDetails.school_name);
    if (teamDetails.roster)
      formData.append("roster", JSON.stringify(teamDetails.roster));
    if (selectedFile) formData.append("avatar", selectedFile);

    try {
      const response = await fetch(
        `${apiBaseUrl}/team/${selectedTeam.team_id}?token=${privateKey}`,
        {
          method: "PUT",
          body: formData,
        }
      );
      const data = await response.json();
      handleImageUpload("logo");
      alert("Team updated:" + data);
    } catch (error) {
      alert("Error updating team: " + error);
    }
  };

  return (
    <Container style={{ maxWidth: "600px", padding: "0 1rem" }}>
      <h1>Edit Team Details</h1>
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
              .sort((a, b) => a.name.localeCompare(b.name)) // Sort teams alphabetically by name
              .map((team) => (
                <option key={team.team_id} value={team.team_id}>
                  {team.name}
                </option>
              ))}
          </Form.Control>
        </Form.Group>

        {teamDetails && (
          <>
            <Form.Group controlId="teamId" className="mb-3">
              <Form.Label>Team ID (cannot be edited)</Form.Label>
              <Form.Control type="text" value={teamDetails.team_id} disabled />
            </Form.Group>

            <Form.Group controlId="teamName" className="mb-3">
              <Form.Label>Team Name</Form.Label>
              <Form.Control
                type="text"
                name="name"
                value={teamDetails.name}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="leader" className="mb-3">
              <Form.Label>Leader</Form.Label>
              <Form.Control
                type="text"
                name="leader"
                value={teamDetails.leader}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="elo" className="mb-3">
              <Form.Label>ELO</Form.Label>
              <Form.Control
                type="number"
                name="elo"
                value={teamDetails.elo}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="playfly_id" className="mb-3">
              <Form.Label>Playfly ID</Form.Label>
              <Form.Control
                type="text"
                name="playfly_id"
                value={teamDetails.playfly_id || ""}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="playfly_participant_id" className="mb-3">
              <Form.Label>Playfly Participant ID</Form.Label>
              <Form.Control
                type="text"
                name="playfly_participant_id"
                value={teamDetails.playfly_participant_id || ""}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="faceit_id" className="mb-3">
              <Form.Label>Faceit ID</Form.Label>
              <Form.Control
                type="text"
                name="faceit_id"
                value={teamDetails.faceit_id || ""}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="school_name" className="mb-3">
              <Form.Label>School Name</Form.Label>
              <Form.Control
                type="text"
                name="school_name"
                value={teamDetails.school_name || ""}
                onChange={handleInputChange}
              />
            </Form.Group>

            <Form.Group controlId="avatar" className="mb-3">
              <Form.Label>Avatar (Upload new avatar)</Form.Label>
              <Form.Control type="file" onChange={handleFileChange} />
              {preview ? (
                <Image src={preview} thumbnail className="mt-2" />
              ) : (
                teamDetails.avatar && (
                  <Image src={teamDetails.avatar} thumbnail className="mt-2" />
                )
              )}
            </Form.Group>
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

        <Button variant="primary" type="submit">
          Update Team
        </Button>
      </Form>
    </Container>
  );
};

export default TeamEditor;
