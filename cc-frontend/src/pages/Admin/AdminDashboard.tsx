import { useEffect, useState } from "react";
import { Alert, Button, Container, Form } from "react-bootstrap";
import DOMPurify from "dompurify";
const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org";

const AdminDashboard = () => {
  const [selectedAlertStyle, setSelectedAlertStyle] = useState("primary");
  const [alertText, setAlertText] = useState("");

  async function fetchInitalAlertText() {
    const response = await fetch(`${apiBaseUrl}/alert`);

    const data = await response.text();
    setAlertText(data);
  }

  useEffect(() => {
    fetchInitalAlertText();
  }, []);

  return (
    <Container style={{ maxWidth: "600px", padding: "0 1rem" }}>
      <h1 className="mb-4">Dashboard</h1>

      <h3>Update Site Data</h3>

      <Button className="mb-2">Update Site Data</Button>

      <h4>Last Updated: </h4>
      <p>null</p>

      <hr />
      <h3>Set Site Alert Message</h3>
      <Form>
        <Form.Label>HTML Enabled :)</Form.Label>
        <Form.Control
          className="mb-3"
          as="textarea"
          style={{ height: "200px" }}
          defaultValue={alertText}
          onChange={(e) => {
            setAlertText(e.currentTarget.value);
          }}
        />
        <Form.Label>Select Color:</Form.Label>
        <Form.Select
          className="mb-3"
          defaultValue=""
          onChange={(e) => {
            setSelectedAlertStyle(e.currentTarget.value);
          }}
        >
          <option key="" value="" disabled>
            Select Color
          </option>
          <option value="primary">Primary</option>
          <option value="secondary">Secondary</option>
          <option value="success">Success</option>
          <option value="danger">Danger</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
          <option value="light">Light</option>
        </Form.Select>
        <h4>Preview</h4>
        <Alert className="mb-3" variant={selectedAlertStyle}>
          <div
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(alertText) }}
          />
        </Alert>
        <Button>Save</Button>
      </Form>
    </Container>
  );
};

export default AdminDashboard;
