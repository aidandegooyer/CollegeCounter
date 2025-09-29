import { BrowserRouter, Route, Routes, Navigate } from "react-router";

import { initializeApp } from "firebase/app";

import { getAuth, onAuthStateChanged } from "firebase/auth";
import { useEffect, useState } from "react";

import Navbar from "@/components/Navbar";
import Home from "@/pages/Home/Home";
import Rankings from "@/pages/Rankings/Rankings";
import Footer from "@/components/Footer";
import Matches from "@/pages/Matches/Matches";
import News from "@/pages/News/News";
import Admin from "@/pages/Admin/Admin";
import SignIn from "@/pages/Admin/SignIn";
import Graphic from "@/pages/Admin/Graphic";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Article from "@/pages/News/Article";
import { Team } from "./pages/Team/Team";
import { NotFoundPage } from "./pages/Utility/NotFoundPage";
import { Match } from "./pages/Match/Match";

const firebaseConfig = {
  apiKey: "AIzaSyDrfCYvSpHIFdvVkVsaMSMgil-d2W9JZWc",
  authDomain: "college-counter-9057f.firebaseapp.com",
  projectId: "college-counter-9057f",
  storageBucket: "college-counter-9057f.firebasestorage.app",
  messagingSenderId: "391353509794",
  appId: "1:391353509794:web:830723864996c2e85bb4fb",
  measurementId: "G-LP3PPN2BT4",
};

const queryClient = new QueryClient();

initializeApp(firebaseConfig);

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const auth = getAuth();
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  if (loading) return null; // or a spinner

  if (!user) return <Navigate to="/signin" replace />;

  return children;
}

function App() {
  return (
    <>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Navbar />

          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/news" element={<News />} />
            <Route path="/news/:slug" element={<Article />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/matches" element={<Matches />} />
            <Route path="/events" element={<Home />} />
            <Route path="/teams/:id" element={<Team />} />
            <Route path="/matches/:id" element={<Match />} />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <Admin />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/graphic"
              element={
                <ProtectedRoute>
                  <Graphic />
                </ProtectedRoute>
              }
            />

            <Route path="/signin" element={<SignIn />} />

            <Route path="*" element={<NotFoundPage />} />
          </Routes>

          <Footer />
        </BrowserRouter>
      </QueryClientProvider>
    </>
  );
}

export default App;
