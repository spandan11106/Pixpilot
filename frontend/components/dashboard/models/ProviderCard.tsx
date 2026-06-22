"use client";

import { useState, useCallback } from "react";

interface ProviderCardProps {
  providerId: string;
  name: string;
  role: string;
  badgeBg: string;
  badgeColor: string;
  initials: string;
  keyValue: string;
  keyNote?: string;
  onKeyChange: (value: string) => void;
  visionModel?: string;
  onVisionModelChange?: (value: string) => void;
}

function EyeIcon({ open }: { open: boolean }) {
  if (open) {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function ProviderCard({
  name,
  role,
  badgeBg,
  badgeColor,
  initials,
  keyValue,
  keyNote = "Stored in .env",
  onKeyChange,
  visionModel,
  onVisionModelChange,
}: ProviderCardProps) {
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  const isConnected = keyValue.trim() !== "";

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(keyValue).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  }, [keyValue]);

  return (
    <article className="prov card">
      <div className="prov-head">
        <span
          className="prov-mark"
          style={{ background: badgeBg, color: badgeColor }}
        >
          {initials}
        </span>
        <div className="prov-id">
          <div className="prov-name">{name}</div>
          <div className="prov-role">{role}</div>
        </div>
        <span className={`conn ${isConnected ? "ok" : "off"}`}>
          {isConnected ? "Connected" : "Not configured"}
        </span>
      </div>

      <div className="field">
        <div className="field-row">
          <span className="field-label">API key</span>
          <span className="caption">{keyNote}</span>
        </div>
        <div className="key-wrap">
          <input
            className="finput mono"
            type={showKey ? "text" : "password"}
            value={keyValue}
            onChange={(e) => onKeyChange(e.target.value)}
            placeholder={`Paste ${name} key…`}
            autoComplete="off"
            aria-label={`${name} API key`}
          />
          <span className="key-tools">
            <button
              className="key-btn"
              type="button"
              onClick={() => setShowKey((v) => !v)}
              aria-label={showKey ? "Hide key" : "Show key"}
            >
              <EyeIcon open={showKey} />
            </button>
            <button
              className={`key-btn${copied ? " copied" : ""}`}
              type="button"
              onClick={handleCopy}
              aria-label="Copy key"
            >
              <svg className="copy-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              <svg className="copied-ck" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </button>
          </span>
        </div>
      </div>

      {visionModel !== undefined && onVisionModelChange && (
        <div className="field vmodel">
          <div className="field-row">
            <span className="field-label">Vision model</span>
            <span className="badge badge-vision">Vision</span>
          </div>
          <input
            className="finput mono"
            type="text"
            value={visionModel}
            onChange={(e) => onVisionModelChange(e.target.value)}
            placeholder="e.g. gpt-4o"
            aria-label={`${name} vision model`}
          />
        </div>
      )}
    </article>
  );
}
