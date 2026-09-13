import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AiAssistant from "./components/AiAssistant.jsx";
import DemoModeBanner from "./components/DemoModeBanner.jsx";
import { useAuth } from "./context/AuthContext.jsx";

import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ResumeUpload from "./pages/ResumeUpload.jsx";
import JobDescription from "./pages/JobDescription.jsx";
import InterviewSetup from "./pages/InterviewSetup.jsx";
import InterviewChat from "./pages/InterviewChat.jsx";
import InterviewReport from "./pages/InterviewReport.jsx";
import PerformanceHistory from "./pages/PerformanceHistory.jsx";

export default function App() {
  const { user, loading } = useAuth();

  return (
    <>
      <Navbar />
      <DemoModeBanner />
      <Routes>
        <Route path="/" element={<Navigate to={user ? "/dashboard" : "/login"} replace />} />
        <Route path="/login" element={loading ? null : user ? <Navigate to="/dashboard" replace /> : <Login />} />
        <Route path="/register" element={loading ? null : user ? <Navigate to="/dashboard" replace /> : <Register />} />

        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/resume" element={<ProtectedRoute><ResumeUpload /></ProtectedRoute>} />
        <Route path="/job-description" element={<ProtectedRoute><JobDescription /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><PerformanceHistory /></ProtectedRoute>} />

        <Route path="/interview/setup" element={<ProtectedRoute><InterviewSetup /></ProtectedRoute>} />
        <Route path="/interview/:interviewId" element={<ProtectedRoute><InterviewChat /></ProtectedRoute>} />
        <Route path="/interview/:interviewId/report" element={<ProtectedRoute><InterviewReport /></ProtectedRoute>} />

        <Route path="*" element={<Navigate to={user ? "/dashboard" : "/login"} replace />} />
      </Routes>
      {user && <AiAssistant />}
    </>
  );
}
