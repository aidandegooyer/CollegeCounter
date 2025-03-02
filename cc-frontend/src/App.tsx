import "./custom.scss";
import Home from "./pages/Home/Home";
import Navigation from "./Nav";
import { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Rankings from "./pages/Rankings/Rankings";
import Matches from "./pages/Matches/Matches";
import Team from "./pages/Team/Team";

function App() {
  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", "dark");
  }, []);

  return (
    <Router>
      <Navigation />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/rankings" element={<Rankings />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/team" element={<Team />} />
      </Routes>
    </Router>
  );
}

export default App;
