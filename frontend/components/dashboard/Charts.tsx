// Throughput line/area chart + rendering-capacity gauge. Static SVG with the
// design's draw-in animations (disabled under prefers-reduced-motion via CSS).

export function ThroughputChart() {
  return (
    <div className="card chart-card">
      <div className="chart-head">
        <div>
          <h2 className="heading-3">Pipeline Throughput</h2>
          <div className="caption">Images rendered per hour · last 12h</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="kpi-num" style={{ fontSize: 24 }}>
            640<span style={{ fontSize: 13, fontWeight: 500, color: "var(--muted-fg)" }}> /hr</span>
          </div>
          <span className="trend up">▲ 18% vs avg</span>
        </div>
      </div>
      <div className="line-chart">
        <svg viewBox="0 0 700 200" preserveAspectRatio="none">
          <line x1="0" y1="50" x2="700" y2="50" stroke="var(--border)" vectorEffect="non-scaling-stroke" />
          <line x1="0" y1="100" x2="700" y2="100" stroke="var(--border)" vectorEffect="non-scaling-stroke" />
          <line x1="0" y1="150" x2="700" y2="150" stroke="var(--border)" vectorEffect="non-scaling-stroke" />
          <defs>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(48,62,210,0.22)" />
              <stop offset="100%" stopColor="rgba(48,62,210,0)" />
            </linearGradient>
          </defs>
          <path
            d="M30,136.6 L89,126.9 L148,114.7 L207,119.6 L266,102.6 L326,90.4 L384,73.4 L444,80.7 L503,63.7 L562,54 L621,41.9 L680,34.6 L680,190 L30,190 Z"
            fill="url(#areaGrad)"
          />
          <polyline
            className="line-draw"
            fill="none"
            stroke="var(--primary)"
            strokeWidth={2.5}
            vectorEffect="non-scaling-stroke"
            strokeLinecap="round"
            strokeLinejoin="round"
            points="30,136.6 89,126.9 148,114.7 207,119.6 266,102.6 326,90.4 384,73.4 444,80.7 503,63.7 562,54 621,41.9 680,34.6"
          />
          <circle cx="680" cy="34.6" r="4" fill="var(--primary)" />
        </svg>
      </div>
      <div className="chart-x">
        <span>09:00</span><span>11:00</span><span>13:00</span>
        <span>15:00</span><span>17:00</span><span>now</span>
      </div>
    </div>
  );
}

export function CapacityGauge() {
  return (
    <div className="card chart-card">
      <div className="chart-head"><h2 className="heading-3">Rendering Capacity</h2></div>
      <div className="gauge-wrap">
        <div className="gauge">
          <svg width={180} height={180} viewBox="0 0 180 180">
            <circle cx="90" cy="90" r="75" fill="none" stroke="var(--border)" strokeWidth={14} />
            <circle
              className="gauge-arc"
              cx="90" cy="90" r="75" fill="none"
              stroke="url(#gaugeGrad)" strokeWidth={14} strokeLinecap="round"
              strokeDasharray="471.2" strokeDashoffset="103.7"
              transform="rotate(-90 90 90)"
            />
            <defs>
              <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="var(--accent-1)" />
                <stop offset="100%" stopColor="var(--accent-2)" />
              </linearGradient>
            </defs>
          </svg>
          <div className="gauge-center">
            <span className="gauge-pct">78%</span>
            <span className="gauge-sub">capacity used</span>
          </div>
        </div>
        <div className="gauge-stats">
          <div className="gauge-stat"><div className="n">6/8</div><div className="caption">Nodes active</div></div>
          <div className="gauge-stat"><div className="n">37</div><div className="caption">In queue</div></div>
        </div>
      </div>
    </div>
  );
}
