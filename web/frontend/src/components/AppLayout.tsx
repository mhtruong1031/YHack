import type { ReactNode } from "react";
import { AppNav } from "./AppNav";

type AppLayoutProps = {
  children: ReactNode;
  /** Sign-in and similar: brand + Home only */
  navMinimal?: boolean;
};

export function AppLayout({ children, navMinimal = false }: AppLayoutProps) {
  return (
    <div className="app-view">
      <AppNav minimal={navMinimal} />
      <main className="app-view-main">
        <div className="app-view-inner">{children}</div>
      </main>
    </div>
  );
}
