import type { ReactNode } from "react";

import "./panel.css";

interface PanelProps {
  title: string;
  /** Stable, language-independent id for the heading. */
  slug: string;
  step?: string;
  aside?: ReactNode;
  children: ReactNode;
}

export function Panel({ title, slug, step, aside, children }: PanelProps) {
  return (
    <section className="panel" aria-labelledby={`panel-${slug}`}>
      <header className="panel__header">
        <h2 className="panel__title" id={`panel-${slug}`}>
          {step && <span className="panel__step">{step}</span>}
          {title}
        </h2>
        {aside}
      </header>
      {children}
    </section>
  );
}
