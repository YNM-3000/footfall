import type { ReactNode } from "react";

import "./panel.css";

interface PanelProps {
  title: string;
  step?: string;
  aside?: ReactNode;
  children: ReactNode;
}

export function Panel({ title, step, aside, children }: PanelProps) {
  return (
    <section className="panel" aria-labelledby={`panel-${title.replace(/\s+/g, "-").toLowerCase()}`}>
      <header className="panel__header">
        <h2 className="panel__title" id={`panel-${title.replace(/\s+/g, "-").toLowerCase()}`}>
          {step && <span className="panel__step">{step}</span>}
          {title}
        </h2>
        {aside}
      </header>
      {children}
    </section>
  );
}
