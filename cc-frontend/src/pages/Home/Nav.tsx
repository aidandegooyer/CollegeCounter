import { Navbar, Nav, Container } from "react-bootstrap";

const Navigation = () => {
  return (
    <Navbar bg="transparent">
      <Container>
        <Nav className="me-auto justify-content-center w-100">
          {" "}
          {/* Add justify-content-center class */}
          <Nav.Link href="#home">Home</Nav.Link>
          <Nav.Link href="#link">Rankings</Nav.Link>
          <Nav.Link href="#link">Blog</Nav.Link>
          <Nav.Link href="#link">Matches</Nav.Link>
        </Nav>
      </Container>
    </Navbar>
  );
};

export default Navigation;
