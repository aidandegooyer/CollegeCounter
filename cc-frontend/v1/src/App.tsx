import "./App.css";
import Navbar from "@/components/Navbar";
import Home from "@/pages/Home/Home";

function App() {
  return (
    <>
      <Navbar />
      <div className="app-container flex justify-center mt-2">
        <Home />
      </div>
    </>
  );
}

export default App;
