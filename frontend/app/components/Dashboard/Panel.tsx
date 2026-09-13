import type { ReactNode } from 'react';

export function Panel({ title, eyebrow, action, children, className = '' }: { title?: string; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`panel ${className}`}>
      {(eyebrow || title || action) && (
        <header className="panel-header">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <h2 className="panel-title">{title}</h2>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
