"use client";

// Enlarged preview shown centered with the rest of the page blurred behind it.
// Clicking the blurred backdrop dismisses it (Esc is handled by the modal so it
// can close the lightbox before the modal itself).
export function Lightbox({ src, onClose }: { src: string; onClose: () => void }) {
  return (
    <div className="lightbox" onClick={onClose}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="Enlarged preview" onClick={(e) => e.stopPropagation()} />
    </div>
  );
}
