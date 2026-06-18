import "./dashboard.css";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { KpiGrid } from "./KpiGrid";
import { ThroughputChart, CapacityGauge } from "./Charts";
import { ActiveJob } from "./ActiveJob";
import { RecentGenerations } from "./RecentGenerations";
import { RenderQueue } from "./RenderQueue";
import { ActivityFeed } from "./ActivityFeed";
import { RefreshIcon, GridIcon } from "./icons";

export function Dashboard() {
  return (
    <div className="pp-dash">
      <div className="app">
        <Sidebar />
        <div className="main">
          <Topbar />
          <main className="content">
            <div className="page-head">
              <div>
                <h1 className="display-l">Image Generation Pipeline</h1>
                <p>Real-time view of jobs moving through prompt, queue, render, and post-processing.</p>
              </div>
              <div style={{ display: "flex", gap: "var(--space-3)" }}>
                <button className="btn btn-ghost"><RefreshIcon /> Refresh</button>
                <button className="btn btn-secondary"><GridIcon /> Manage Queue</button>
              </div>
            </div>

            <KpiGrid />

            <section className="charts">
              <ThroughputChart />
              <CapacityGauge />
            </section>

            <ActiveJob />

            <div className="cols">
              <RecentGenerations />
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
                <RenderQueue />
                <ActivityFeed />
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
