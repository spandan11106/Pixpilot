import { generations, type Generation } from "./data";
import { ImageIcon, AlertIcon, ChevronRightIcon, RefreshIcon } from "./icons";

function StatusBadge({ gen }: { gen: Generation }) {
  switch (gen.status.kind) {
    case "done":
      return <span className="badge badge-success">Done</span>;
    case "upscaling":
      return <span className="badge badge-amber"><span className="pulse" />Upscaling</span>;
    case "failed":
      return <span className="badge badge-error">Failed</span>;
  }
}

function GenerationCard({ gen }: { gen: Generation }) {
  const failed = gen.status.kind === "failed";
  return (
    <article className="gen">
      <div
        className={`thumb ${gen.thumb}`}
        style={failed ? { background: "rgba(220,38,38,0.07)" } : undefined}
      >
        <StatusBadge gen={gen} />
        {failed
          ? <AlertIcon stroke="var(--destructive)" />
          : <ImageIcon strokeWidth={1.6} />}
      </div>
      <div className="gen-body">
        <p className="gen-prompt">{gen.prompt}</p>
        <div className="gen-meta">
          <span className="caption">{gen.meta}</span>
          {failed ? (
            <button className="btn btn-ghost btn-sm" style={{ height: 22, padding: "0 8px", color: "var(--destructive)" }}>
              <RefreshIcon /> Retry
            </button>
          ) : (
            <span className="caption">{gen.time}</span>
          )}
        </div>
      </div>
    </article>
  );
}

export function RecentGenerations() {
  return (
    <section className="card">
      <div className="section-head">
        <h2 className="heading-2">Recent Generations</h2>
        <button className="btn btn-ghost btn-sm">View all <ChevronRightIcon /></button>
      </div>
      <div className="gen-grid">
        {generations.map((gen) => <GenerationCard key={gen.id} gen={gen} />)}
      </div>
    </section>
  );
}
