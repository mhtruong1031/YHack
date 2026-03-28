import type { ReactNode } from "react";

type MacWindowProps = {
  title: string;
  children: ReactNode;
  className?: string;
};

export function MacWindow({ title, children, className = "" }: MacWindowProps) {
  return (
    <div className={`mac-window ${className}`.trim()}>
      <div className="mac-titlebar">
        <div className="mac-traffic" aria-hidden>
          <span className="dot close" />
          <span className="dot min" />
          <span className="dot max" />
        </div>
        <div className="mac-title">{title}</div>
        <div className="mac-title-spacer" />
      </div>
      <div className="mac-content">{children}</div>
      <style>{`
        .mac-window {
          width: min(960px, 100%);
          height: min(85vh, 820px);
          min-height: 320px;
          display: flex;
          flex-direction: column;
          border-radius: 12px;
          overflow: hidden;
          background: var(--glass-bg);
          backdrop-filter: blur(10px) saturate(1.12);
          -webkit-backdrop-filter: blur(10px) saturate(1.12);
          border: 1px solid var(--glass-border);
          box-shadow: var(--glass-shadow);
        }
        .mac-titlebar {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.55rem 0.75rem;
          background: rgba(0, 0, 0, 0.22);
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          flex-shrink: 0;
        }
        .mac-traffic {
          display: flex;
          gap: 6px;
          align-items: center;
        }
        .mac-traffic .dot {
          width: 11px;
          height: 11px;
          border-radius: 50%;
          box-shadow: inset 0 0 0 0.5px rgba(0, 0, 0, 0.25);
        }
        .mac-traffic .close {
          background: #ff5f57;
        }
        .mac-traffic .min {
          background: #febc2e;
        }
        .mac-traffic .max {
          background: #28c840;
        }
        .mac-title {
          flex: 1;
          text-align: center;
          font-size: 0.8rem;
          font-weight: 600;
          color: var(--text-muted);
          letter-spacing: 0.02em;
        }
        .mac-title-spacer {
          width: 52px;
          flex-shrink: 0;
        }
        .mac-content {
          padding: 1.25rem 1.5rem;
          overflow: auto;
          flex: 1;
          min-height: 0;
        }
      `}</style>
    </div>
  );
}
