import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="w-9 h-9 rounded-full flex items-center justify-center text-slate hover:text-ink hover:bg-ink/5 transition-colors"
    >
      {isDark ? (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1.5m0 15V21m8.485-9H19.5M4.5 12H3m14.834-6.364l-1.06 1.06M6.226 17.774l-1.06 1.06m0-13.668l1.06 1.06M17.774 17.774l1.06 1.06M16.5 12a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
        </svg>
      )}
    </button>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="border-b border-border/10 bg-surface">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="font-display text-xl text-ink">
          Prepwell
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {user && (
            <>
              <Link to="/dashboard" className="text-slate hover:text-ink">Dashboard</Link>
              <Link to="/history" className="text-slate hover:text-ink">History</Link>
              <span className="text-slate hidden sm:inline">{user.full_name || user.email}</span>
            </>
          )}
          <ThemeToggle />
          {user && (
            <button onClick={handleLogout} className="btn-secondary py-1.5 px-3.5 text-sm">
              Log out
            </button>
          )}
        </nav>
      </div>
    </header>
  );
}
