"use client";

import { useState } from "react";
import { queueItems as initialItems, type QueueItem } from "./data";
import { ChevronDownIcon, GripIcon, ImageIcon } from "./icons";

export function RenderQueue() {
  const [collapsed, setCollapsed] = useState(false);
  const [items, setItems] = useState<QueueItem[]>(initialItems);
  const [dragId, setDragId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  function handleDrop(targetId: string) {
    if (!dragId || dragId === targetId) {
      setDragId(null);
      setOverId(null);
      return;
    }
    setItems((prev) => {
      const next = [...prev];
      const from = next.findIndex((i) => i.id === dragId);
      const to = next.findIndex((i) => i.id === targetId);
      if (from === -1 || to === -1) return prev;
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
    setDragId(null);
    setOverId(null);
  }

  return (
    <section className="card queue">
      <div className="section-head">
        <h3 className="heading-3">Render Queue</h3>
        <span className="badge badge-default">37</span>
      </div>
      <button
        className={`group-head ${collapsed ? "collapsed" : ""}`}
        onClick={() => setCollapsed((c) => !c)}
      >
        <ChevronDownIcon className="chev" />
        Priority batch · Product Launch
        <span className="badge badge-accent" style={{ marginLeft: "auto" }}>{items.length} jobs</span>
      </button>
      <div className={`queue-list ${collapsed ? "collapsed" : ""}`}>
        {items.map((item) => (
          <div
            key={item.id}
            className={`queue-item ${dragId === item.id ? "dragging" : ""} ${overId === item.id && dragId !== item.id ? "drag-over" : ""}`}
            draggable
            onDragStart={() => setDragId(item.id)}
            onDragEnd={() => { setDragId(null); setOverId(null); }}
            onDragOver={(e) => { e.preventDefault(); if (item.id !== dragId) setOverId(item.id); }}
            onDragLeave={() => setOverId((id) => (id === item.id ? null : id))}
            onDrop={(e) => { e.preventDefault(); handleDrop(item.id); }}
          >
            <span className="q-handle"><GripIcon /></span>
            <span className={`q-thumb ${item.thumb}`}><ImageIcon strokeWidth={1.6} /></span>
            <div className="q-info">
              <div className="q-title">{item.title}</div>
              <div className="q-prog"><i style={{ width: `${item.progress}%` }} /></div>
              <div className="q-eta">{item.eta}</div>
            </div>
            <span className="caption">{item.progress}%</span>
          </div>
        ))}
      </div>
    </section>
  );
}
