import "./custom.scss";
import Home from "./pages/Home/Home";
import Navigation from "./pages/Home/Nav";
import { useEffect } from "react";

function App() {
  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", "dark");
  }, []);

  return (
    <>
      <Navigation />
      <Home />
    </>
  );
}

export default App;
