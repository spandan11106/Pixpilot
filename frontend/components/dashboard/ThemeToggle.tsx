"use client";

/* Light/dark toggle for the dashboard. Flips `data-theme` on <html> (the same
   attribute the no-flash script in app/layout.tsx sets) and persists the choice
   to localStorage under `pixpilot-theme`. The sun/moon icons are swapped via CSS
   (`.theme-sun` / `.theme-moon`) based on the active theme. */
export function ThemeToggle() {
  const toggle = () => {
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("pixpilot-theme", next);
    } catch {
      /* ignore storage failures (private mode, etc.) */
    }
  };

  return (
    <button
      type="button"
      className="icon-btn"
      onClick={toggle}
      aria-label="Toggle light or dark theme"
    >
      <svg
        className="theme-sun"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
      </svg>
      <svg
        className="theme-moon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    </button>
  );
}
