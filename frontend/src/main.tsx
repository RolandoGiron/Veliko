import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { LoginPage } from "./pages/LoginPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProjectPage } from "./pages/ProjectPage";

const qc = new QueryClient();

function Guard({ children }: { children: React.JSX.Element }) {
  return localStorage.getItem("velvyko_token") ? children : <Navigate to="/login" />;
}

function App() {
  const { email } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={email ? <Navigate to="/" /> : <LoginPage />} />
      <Route path="/" element={<Guard><ProjectsPage /></Guard>} />
      <Route path="/projects/:id" element={<Guard><ProjectPage /></Guard>} />
    </Routes>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AuthProvider><App /></AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
