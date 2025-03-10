import { Navbar, Container, Nav, Image } from "react-bootstrap";
import { Link } from "react-router-dom";
import logo from "./assets/0.1x/C Logo@0.1x.png"; // Adjust the path to your logo image

const Navigation = () => {
  return (
    <>
      <Navbar bg="dark" variant="dark" sticky="top">
        <Container fluid>
          <Navbar.Brand as={Link} to="/">
            <div className="d-none d-md-flex" style={{ width: "200px" }}>
              <Image
                src={logo}
                alt="logo"
                style={{ height: "30px", marginRight: "5px" }}
                fluid
              />
              College Counter
            </div>
            <div className="d-block d-md-none">
              <Image src={logo} alt="logo" style={{ height: "30px" }} fluid />
            </div>
          </Navbar.Brand>
          <Nav className="">
            <Nav.Link as={Link} to="/">
              Home
            </Nav.Link>
            <Nav.Link as={Link} to="/rankings">
              Rankings
            </Nav.Link>
            <Nav.Link as={Link} to="/matches">
              Matches
            </Nav.Link>
            <Nav.Link as={Link} to="/results">
              Results
            </Nav.Link>
          </Nav>

          <input
            type="text"
            placeholder="Search is disabled"
            className="form-control d-none d-md-flex justify-content-end"
            style={{ maxWidth: "200px" }}
            disabled
          />
        </Container>
      </Navbar>

      {/* Search bar for smaller screens (below the navbar) */}
      <div className="d-block d-md-none bg-dark py-2">
        <Container>
          <input
            type="text"
            placeholder="Search is disabled"
            className="form-control"
            disabled
          />
        </Container>
      </div>
    </>
  );
};

export default Navigation;
