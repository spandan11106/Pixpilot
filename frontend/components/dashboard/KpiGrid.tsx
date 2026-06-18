import { kpis, type Kpi } from "./data";
import { ImageIcon, ClockIcon, TargetIcon, CheckCircleIcon } from "./icons";

const iconFor = {
  image: ImageIcon,
  clock: ClockIcon,
  target: TargetIcon,
  check: CheckCircleIcon,
} as const;

function KpiCard({ kpi }: { kpi: Kpi }) {
  const Icon = iconFor[kpi.icon];
  const arrow = kpi.trend.dir === "up" ? "▲" : "▼";
  return (
    <div className="card kpi">
      <div className="kpi-top">
        <div className="kpi-icon" style={{ background: kpi.iconBg, color: kpi.iconColor }}>
          <Icon />
        </div>
        <span className={`trend ${kpi.trend.dir}`}>{arrow} {kpi.trend.label}</span>
      </div>
      <div className="kpi-num">{kpi.value}</div>
      <div className="kpi-label">{kpi.label}</div>
      <div className="kpi-spark">
        <svg viewBox="0 0 100 34" preserveAspectRatio="none">
          <polyline
            fill="none"
            stroke={kpi.sparkColor}
            strokeWidth={2}
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={kpi.sparkPoints}
          />
        </svg>
      </div>
    </div>
  );
}

export function KpiGrid() {
  return (
    <section className="kpi-grid">
      {kpis.map((kpi) => <KpiCard key={kpi.id} kpi={kpi} />)}
    </section>
  );
}
