"use client";

import { useEffect, useRef, useState } from "react";

export interface SSEMessage {
  event: string;
  data: Record<string, unknown>;
  timestamp: number;
}

export function useSSE(runId: string | null) {
  const [messages, setMessages] = useState<SSEMessage[]>([]);
  const [latest, setLatest] = useState<SSEMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;

    const url = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/runs/${runId}/events`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setConnected(true);

    source.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data) as { event: string; data: Record<string, unknown> };
        const msg: SSEMessage = { ...parsed, timestamp: Date.now() };
        setMessages((prev) => [...prev, msg]);
        setLatest(msg);

        if (parsed.event === "stream_end") {
          source.close();
          setConnected(false);
        }
      } catch {
        // malformed event — ignore
      }
    };

    source.onerror = () => {
      setConnected(false);
      source.close();
    };

    return () => {
      source.close();
      setConnected(false);
    };
  }, [runId]);

  return { messages, latest, connected };
}
