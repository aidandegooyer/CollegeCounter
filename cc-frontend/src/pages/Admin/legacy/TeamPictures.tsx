import React, { useEffect, useState } from "react";
import { Container, Form, Button, Image } from "react-bootstrap";
import { Team } from "../../../types";

const TeamPictures: React.FC = () => {
  const [Teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [selectedPic, setSelectedPic] = useState<string>("");
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
    if (selectedFile && selectedPic && selectedTeam) {
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

          <Form.Label>Select Picture Type</Form.Label>
          <Form.Control
            as="select"
            value={selectedPic}
            onChange={(e) => {
              const pic = e.target.value;
              setSelectedPic(pic);
            }}
          >
            <option value="" disabled>
              Select a picture type
            </option>
            <option value="logo">logo</option>
            <option value="bg">background</option>
          </Form.Control>

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

export default TeamPictures;
