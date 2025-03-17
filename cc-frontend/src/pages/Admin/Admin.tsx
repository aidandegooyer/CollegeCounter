import React from "react";
import { Tabs, Tab, Container } from "react-bootstrap";
import TeamSettings from "./TeamSettings";
import PlayerSettings from "./PlayerSettings";
import AdminDashboard from "./AdminDashboard";

const Admin: React.FC = () => {
  return (
    <Container style={{ maxWidth: "800px" }}>
      <h1>Admin Control Panel</h1>
      <Tabs defaultActiveKey="dashboard" id="admin-control-panel">
        <Tab eventKey="dashboard" title="Dashboard">
          <Container style={{ marginTop: "20px", padding: "20px" }}>
            <AdminDashboard />
          </Container>
        </Tab>
        <Tab eventKey="teams" title="Teams">
          <Container style={{ marginTop: "20px", padding: "20px" }}>
            <TeamSettings />
          </Container>
        </Tab>
        <Tab eventKey="player" title="Player">
          <Container style={{ marginTop: "20px", padding: "20px" }}>
            <PlayerSettings />
          </Container>
        </Tab>
        <Tab eventKey="settings" title="Settings">
          <Container style={{ marginTop: "20px", padding: "20px" }}>
            <h2>Settings</h2>
            <p>Configure system settings here.</p>
          </Container>
        </Tab>
      </Tabs>
    </Container>
  );
};

export default Admin;
