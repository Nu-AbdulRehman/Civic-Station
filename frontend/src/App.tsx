import { NavLink, Route, Routes, useLocation } from "react-router";
import ErrorBoundary from "./components/ErrorBoundary";
import DashboardPage from "./pages/DashboardPage";
import StatsPage from "./pages/StatsPage";
import SubmitPage from "./pages/SubmitPage";

export default function App() {
  const { pathname } = useLocation();
  return (
    <div className="shell">
      <header>
        <h1>Civic-Station</h1>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Submit
          </NavLink>
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/stats">Stats</NavLink>
        </nav>
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
    </div>
  );
}
