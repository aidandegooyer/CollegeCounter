import { Navbar, Container, Nav, Image, Button } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";
import logo from "./assets/0.1x/C Logo@0.1x.png"; // Adjust the path to your logo image

const Navigation = () => {
  const navigate = useNavigate();

  function handleSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const search = new FormData(e.currentTarget).get("search") as string;
    if (!search || search === "") return;
    navigate(`/search?query=${encodeURIComponent(search)}`);
  }

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
            <Nav.Link as={Link} to="/rankings">
              Rankings
            </Nav.Link>
            <Nav.Link as={Link} to="/matches">
              Matches
            </Nav.Link>
            <Nav.Link as={Link} to="/results">
              Results
            </Nav.Link>
            <Nav.Link as={Link} to="/events">
              Events
            </Nav.Link>
          </Nav>

          <form onSubmit={handleSearch} className="d-flex d-none d-md-block">
            <div className="input-group">
              <input
                type="text"
                name="search"
                placeholder="Search"
                className="form-control"
              />
              <Button variant="outline-secondary" type="submit">
                <i className="bi bi-search"></i>
              </Button>
            </div>
          </form>
        </Container>
      </Navbar>

      {/* Search bar for smaller screens (below the navbar) */}
      <div className="d-block d-md-none bg-dark py-2">
        <Container>
          <form onSubmit={handleSearch} className="d-flex">
            <div className="input-group">
              <input
                type="text"
                name="search"
                placeholder="Search"
                className="form-control"
              />
              <Button variant="outline-secondary" type="submit">
                <i className="bi bi-search"></i>
              </Button>
            </div>
          </form>
        </Container>
      </div>
    </>
  );
};

export default Navigation;
