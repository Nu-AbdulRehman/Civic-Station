import { useEffect } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router";
import ErrorBoundary from "./components/ErrorBoundary";
import SiteFooter from "./components/SiteFooter";
import ThemeToggle from "./components/ThemeToggle";
import DashboardPage from "./pages/DashboardPage";
import StatsPage from "./pages/StatsPage";
import SubmitPage from "./pages/SubmitPage";

// Browser-tab title per route: "Dashboard · Civic-Station".
const PAGE_TITLE: Record<string, string> = { "/": "Submit", "/dashboard": "Dashboard", "/stats": "Stats" };

export default function App() {
  const { pathname } = useLocation();
  useEffect(() => {
    const page = PAGE_TITLE[pathname];
    document.title = page ? `${page} · Civic-Station` : "Civic-Station";
  }, [pathname]);
  return (
    <div className="shell">
      <header>
        <h1>
          <img src="/favicon.svg" alt="" />
          Civic-Station <span className="muted">Complaint triage</span>
        </h1>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Submit
          </NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/stats">Stats</NavLink>
        </nav>
        <ThemeToggle />
      </header>
      <main>
        {/* Inside <main>, not around the shell: navigation survives a crashed view. */}
        <ErrorBoundary resetKey={pathname}>
          <Routes>
            <Route path="/" element={<SubmitPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/stats" element={<StatsPage />} />
          </Routes>
        </ErrorBoundary>
      </main>
      <SiteFooter />
    </div>
  );
}
