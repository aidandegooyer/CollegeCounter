import React, { useEffect, lazy, Suspense } from "react";
import "./custom.scss";
import Navigation from "./Nav";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Footer from "./Footer";
import ScrollToTop from "./ScrollToTop";

// Lazy load route components
const Home = lazy(() => import("./pages/Home/Home"));
const Rankings = lazy(() => import("./pages/Rankings/Rankings"));
const Matches = lazy(() => import("./pages/Matches/Matches"));
const TeamPage = lazy(() => import("./pages/Team/TeamPage"));
const Results = lazy(() => import("./pages/Results/Results"));
const Blog = lazy(() => import("./pages/Blog/Blog"));
const BlogPage = lazy(() => import("./pages/Blog/BlogPage"));
const Search = lazy(() => import("./pages/Search/Search"));
const Admin = lazy(() => import("./pages/Admin/Admin"));
const NotFoundPage = lazy(() => import("./pages/utils/NotFoundPage"));

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
        {/* Suspense wrapper for lazy loaded routes */}
        <Suspense fallback={<div>Loading...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/blog" element={<Blog />} />
            <Route path="/blog/:slug" element={<BlogPage />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/matches" element={<Matches />} />
            <Route path="/team" element={<TeamPage />} />
            <Route path="/results" element={<Results />} />
            <Route path="/search" element={<Search />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </Router>
      <Footer />
    </QueryClientProvider>
  );
}

export default App;
