import { activityItems, type ActivityItem } from "./data";
import { RefreshIcon } from "./icons";

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <div className="act-item">
      <span className="act-av" style={{ background: item.avatarBg, color: item.avatarColor }}>
        {item.avatar}
      </span>
      <div className="act-body">
        <p className="act-text">
          {item.body.map((part, i) =>
            part.bold ? <b key={i}>{part.text}</b> : <span key={i}>{part.text}</span>
          )}
          {item.badge && <span className="badge badge-error">{item.badge}</span>}
        </p>
        {item.failed ? (
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginTop: 6 }}>
            <span className="caption">{item.time}</span>
            <button className="btn btn-outline btn-sm"><RefreshIcon /> Retry</button>
          </div>
        ) : (
          <span className="caption">{item.time}</span>
        )}
      </div>
    </div>
  );
}

export function ActivityFeed() {
  return (
    <section className="card activity">
      <div className="section-head"><h3 className="heading-3">Activity</h3></div>
      {activityItems.map((item) => <ActivityRow key={item.id} item={item} />)}
    </section>
  );
}
