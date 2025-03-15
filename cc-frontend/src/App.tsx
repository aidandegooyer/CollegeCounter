import "./custom.scss";
import Home from "./pages/Home/Home";
import Navigation from "./Nav";
import { useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Rankings from "./pages/Rankings/Rankings";
import Matches from "./pages/Matches/Matches";
import TeamPage from "./pages/Team/TeamPage";
import Results from "./pages/Results/Results";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UserPicture from "./pages/admin/UserPicture";
import TeamPictures from "./pages/admin/TeamPictures";
import Footer from "./Footer";
import TeamName from "./pages/admin/TeamName";
import Blog from "./pages/Blog/Blog";
import BlogPage from "./pages/Blog/BlogPage";
import ScrollToTop from "./ScrollToTop";

function App() {
  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", "dark");
  }, []);

  const queryClient = new QueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Navigation />
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/blog/:slug" element={<BlogPage />} />
          <Route path="/rankings" element={<Rankings />} />
          <Route path="/matches" element={<Matches />} />
          <Route path="/team" element={<TeamPage />} />
          <Route path="/results" element={<Results />} />
          <Route path="/admin/player" element={<UserPicture />} />
          <Route path="/admin/team" element={<TeamPictures />} />
          <Route path="/admin/team/name" element={<TeamName />} />
        </Routes>
      </Router>
      <Footer />
    </QueryClientProvider>
  );
}

export default App;
