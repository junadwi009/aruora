import React, { useEffect, useState } from "react";
import { api } from "../../lib/api/client";
import type { CefrBand } from "../ui/LevelChip";
import { ViewProvider, useView, type View } from "./viewContext";
import { Sidebar } from "./Sidebar";
import { BottomTabs } from "./BottomTabs";
import { Home } from "./Home";
import { Reading } from "../reading/Reading";
import { Listening } from "../listening/Listening";
import { Writing } from "../writing/Writing";
import { Speaking } from "../speaking/Speaking";
import { Tips } from "../tips/Tips";
import { Progress } from "../progress/Progress";
import { Session } from "../session/Session";
import { MockTest } from "../test/MockTest";
import { Pronounce } from "../pronounce/Pronounce";

// ---------------------------------------------------------------------------
// View registry — Task 21: real skill screens wired in.
// ---------------------------------------------------------------------------
function Placeholder({ name }: { name: string }) {
  return (
    <main className="flex-1 flex items-center justify-center p-6">
      <p className="text-[var(--color-muted)] capitalize">{name}</p>
    </main>
  );
}

type ViewRegistry = {
  [V in View]: (levels: Record<string, CefrBand>) => React.ReactNode;
};

const viewRegistry: ViewRegistry = {
  home: (levels) => <Home levels={levels} />,
  reading: (levels) => <Reading band={levels.reading ?? "B2"} />,
  listening: (levels) => <Listening band={levels.listening ?? "B1"} />,
  speaking: () => <Speaking />,
  writing: () => <Writing />,
  test: () => <MockTest />,
  tips: () => <Tips />,
  progress: () => <Progress />,
  session: () => <Session />,
  pronounce: () => <Pronounce />,
  settings: () => <Placeholder name="Settings" />,
};

// ---------------------------------------------------------------------------
// Inner shell — consumes view context
// ---------------------------------------------------------------------------
function ShellInner({ levels }: { levels: Record<string, CefrBand> }) {
  const { view } = useView();
  const content = viewRegistry[view](levels);

  return (
    <div className="flex h-screen bg-[var(--color-bg)]">
      {/* Sidebar — desktop only */}
      <div className="hidden md:flex">
        <Sidebar levels={levels} />
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {content}
      </div>

      {/* Bottom tabs — mobile only */}
      <div className="md:hidden">
        <BottomTabs />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AppShell — loads skill levels, provides view context
// ---------------------------------------------------------------------------
export function AppShell() {
  const [levels, setLevels] = useState<Record<string, CefrBand>>({});

  useEffect(() => {
    let active = true;
    api
      .skillLevels()
      .then((data) => {
        if (!active) return;
        const map: Record<string, CefrBand> = {};
        for (const { skill, band } of data) {
          map[skill] = band as CefrBand;
        }
        setLevels(map);
      })
      .catch(() => {
        /* tolerate empty — show shell without chips */
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <ViewProvider>
      <ShellInner levels={levels} />
    </ViewProvider>
  );
}
