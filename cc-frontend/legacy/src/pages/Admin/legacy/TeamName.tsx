import React, { useEffect, useState } from "react";
import { Container, Form, Button } from "react-bootstrap";
import { Team } from "../../../types";

const TeamPictures: React.FC = () => {
  const [Teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [privateKey, setPrivateKey] = useState<string | null>(null);
  const [schoolName, setSchoolName] = useState<string>("");

  const apiBaseUrl =
    import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

  const handleSecretKeyChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const key = event.target.value;
    setPrivateKey(key);
  };

  const handleSchoolNameChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const name = event.target.value;
    setSchoolName(name);
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedTeam && schoolName) {
      const formData = new FormData();
      formData.append("team_id", selectedTeam.team_id);
      formData.append("school_name", schoolName);

      fetch(`${apiBaseUrl}/set_school_name?token=${privateKey}`, {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Success:", data);
          alert("Success!");
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("Error!");
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
          <Form.Label>Enter secret key</Form.Label>
          <Form.Control type="text" onChange={handleSecretKeyChange} />
          <Form.Label>Enter school name</Form.Label>
          <Form.Control type="text" onChange={handleSchoolNameChange} />
        </Form.Group>

        <Button variant="primary" type="submit">
          Submit
        </Button>
      </Form>
    </Container>
  );
};

export default TeamPictures;
