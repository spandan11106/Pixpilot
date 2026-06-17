"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useSSE } from "@/lib/sse";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { messages, connected } = useSSE(runId);

  async function startRun() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/runs`, { method: "POST" });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const { run_id } = await res.json();
      setRunId(run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-3xl space-y-8">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">Pixpilot</h1>
          <p className="text-muted-foreground text-lg">
            AI-assisted product image &amp; copy generation pipeline
          </p>
        </div>

        <Separator />

        <Card>
          <CardHeader>
            <CardTitle>New Run</CardTitle>
            <CardDescription>
              Start the pipeline to generate product images and copy.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={startRun} disabled={loading || !!runId}>
              {loading ? "Starting…" : runId ? "Run Started" : "Start Run"}
            </Button>
            {error && <p className="text-destructive text-sm">{error}</p>}
          </CardContent>
        </Card>

        {runId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Pipeline Events</CardTitle>
                <Badge variant={connected ? "default" : "secondary"}>
                  {connected ? "Connected" : "Done"}
                </Badge>
              </div>
              <CardDescription className="font-mono text-xs">{runId}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-muted rounded-md p-4 space-y-2 max-h-80 overflow-y-auto font-mono text-sm">
                {messages.length === 0 && (
                  <p className="text-muted-foreground">Waiting for events…</p>
                )}
                {messages.map((msg, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-primary font-semibold">[{msg.event}]</span>
                    <span className="text-muted-foreground break-all">
                      {JSON.stringify(msg.data)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
