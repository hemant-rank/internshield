"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

export default function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isLightTheme, setIsLightTheme] = useState(false);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("internshield-theme");
    const useLightTheme = savedTheme === "light";
    setIsLightTheme(useLightTheme);
    document.documentElement.dataset.theme = useLightTheme ? "light" : "dark";
  }, []);

  const toggleTheme = () => {
    const useLightTheme = !isLightTheme;
    setIsLightTheme(useLightTheme);
    document.documentElement.dataset.theme = useLightTheme ? "light" : "dark";
    window.localStorage.setItem("internshield-theme", useLightTheme ? "light" : "dark");
  };

  // Close menu when route changes
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Close menu when clicking a hash link (same-page scroll)
  const handleLinkClick = () => {
    setMenuOpen(false);
  };

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link href="/" className="navbar-logo">
          <div className="logo-icon">🛡️</div>
          <span>InternShield</span>
        </Link>

        {/* Hamburger button — only visible on mobile */}
        <button
          className={`hamburger ${menuOpen ? "open" : ""}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle navigation menu"
          aria-expanded={menuOpen}
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>

        {/* Navigation links */}
        <div className={`navbar-links ${menuOpen ? "navbar-links--open" : ""}`}>
          <Link
            href="/#analyze"
            className={`nav-link ${pathname === "/" ? "active" : ""}`}
            onClick={handleLinkClick}
          >
            🔍 Verify
          </Link>
          <Link
            href="/#education"
            className="nav-link"
            onClick={handleLinkClick}
          >
            📖 Learn
          </Link>
          <Link
            href="/#about"
            className="nav-link"
            onClick={handleLinkClick}
          >
            💡 About
          </Link>
          <Link
            href="/history"
            className={`nav-link ${pathname === "/history" ? "active" : ""}`}
            onClick={handleLinkClick}
          >
            📋 History
          </Link>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={isLightTheme ? "Switch to dark theme" : "Switch to light theme"}
            title={isLightTheme ? "Switch to dark theme" : "Switch to light theme"}
          >
            <span aria-hidden="true">{isLightTheme ? "🌙" : "☀️"}</span>
            <span>{isLightTheme ? "Dark" : "Light"}</span>
          </button>
        </div>

        {/* Overlay backdrop for mobile menu */}
        {menuOpen && (
          <div
            className="navbar-overlay"
            onClick={() => setMenuOpen(false)}
          />
        )}
      </div>
    </nav>
  );
}
