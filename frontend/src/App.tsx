import { NavLink, Route, Routes } from "react-router";
import DashboardPage from "./pages/DashboardPage";
import StatsPage from "./pages/StatsPage";
import SubmitPage from "./pages/SubmitPage";

export default function App() {
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
        <Routes>
          <Route path="/" element={<SubmitPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/stats" element={<StatsPage />} />
        </Routes>
      </main>
    </div>
  );
}
