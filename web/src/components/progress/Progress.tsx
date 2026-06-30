import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp, PenLine, Mic } from "lucide-react";
import { api } from "../../lib/api/client";
import type { AttemptSummary, AttemptDetail, Trends, WritingEval, SpeakingEval, MockScore } from "../../lib/types";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Dialog } from "../ui/Dialog";
import { LevelChip } from "../ui/LevelChip";
import type { CefrBand } from "../ui/LevelChip";
import { useView } from "../menu/viewContext";
import { FeedbackView } from "../writing/Writing";
import { SpeakingFeedback } from "../speaking/Speaking";

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getDate()).padStart(2, "0")} ${String(
    d.getHours()
  ).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// Merge writing+speaking points into one time-ordered series for the chart.
function buildChartData(trends: Trends) {
  const rows = [
    ...trends.writing.map((p) => ({ ...p, skill: "writing" as const })),
    ...trends.speaking.map((p) => ({ ...p, skill: "speaking" as const })),
  ].sort((a, b) => (a.createdAt ?? "").localeCompare(b.createdAt ?? ""));
  return rows.map((p) => ({
    t: fmtDate(p.createdAt),
    writing: p.skill === "writing" ? p.overall : null,
    speaking: p.skill === "speaking" ? p.overall : null,
  }));
}

export const Progress: React.FC = () => {
  const { setView } = useView();
  const [loading, setLoading] = useState(true);
  const [trends, setTrends] = useState<Trends>({ writing: [], speaking: [] });
  const [history, setHistory] = useState<AttemptSummary[]>([]);
  const [mocks, setMocks] = useState<MockScore[]>([]);
  const [detail, setDetail] = useState<AttemptDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.statsTrends(), api.historyAttempts(), api.mocksList()])
      .then(([tr, h, m]) => {
        if (cancelled) return;
        setTrends(tr);
        setHistory(h);
        setMocks(m);
      })
      .catch(() => {
        /* leave empty-state */
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const chartData = useMemo(() => buildChartData(trends), [trends]);
  const hasData = history.length > 0 || mocks.length > 0;

  const openDetail = async (id: number) => {
    setDetailLoading(true);
    try {
      setDetail(await api.historyAttempt(id));
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div
        className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10"
        style={{ boxShadow: "var(--shadow-e1)" }}
      >
        <h1 className="text-base font-semibold text-[var(--color-text)] tracking-tight">Progress</h1>
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        {loading ? (
          <Card className="py-12 text-center text-sm text-[var(--color-muted)]">Loading your history…</Card>
        ) : !hasData ? (
          <Card className="flex flex-col items-center gap-5 py-12 text-center">
            <div
              className="flex items-center justify-center w-14 h-14 rounded-[var(--radius-xl)]"
              style={{ background: "color-mix(in srgb, var(--color-primary-600) 12%, transparent)" }}
              aria-hidden="true"
            >
              <TrendingUp size={26} className="text-[var(--color-primary-600)]" />
            </div>
            <div className="flex flex-col gap-2">
              <p className="text-base font-semibold text-[var(--color-text)]">No attempts yet</p>
              <p className="text-sm text-[var(--color-muted)] max-w-xs leading-relaxed">
                Your Writing and Speaking history, band trends, and analytics will appear here once you
                complete your first practice session.
              </p>
            </div>
            <Button onClick={() => setView("writing")}>Start practising</Button>
          </Card>
        ) : (
          <>
            {/* Trend chart */}
            {chartData.length > 0 && (
            <Card>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">
                  Band trend
                </p>
                <span className="text-[11px] text-[var(--color-muted)]">estimates</span>
              </div>
              <div className="h-64" aria-hidden="true">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="t" tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
                    <YAxis domain={[0, 9]} ticks={[0, 3, 5, 6, 7, 9]} tick={{ fontSize: 11 }} stroke="var(--color-muted)" />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="writing" name="Writing" stroke="var(--color-primary-600)" connectNulls dot />
                    <Line type="monotone" dataKey="speaking" name="Speaking" stroke="#0d9488" connectNulls dot />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              {/* a11y data table mirror */}
              <table className="sr-only">
                <caption>Band estimates over time</caption>
                <thead>
                  <tr><th>Date</th><th>Writing</th><th>Speaking</th></tr>
                </thead>
                <tbody>
                  {chartData.map((r, i) => (
                    <tr key={i}><td>{r.t}</td><td>{r.writing ?? "—"}</td><td>{r.speaking ?? "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            </Card>
            )}

            {/* Mock tests */}
            {mocks.length > 0 && (
              <Card>
                <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
                  Mock tests
                </p>
                <ul className="flex flex-col divide-y divide-[var(--color-border)]">
                  {mocks.map((m) => (
                    <li key={m.id} className="flex items-center gap-3 py-2.5 text-sm">
                      <span className="flex-1 text-xs text-[var(--color-muted)]">{fmtDate(m.createdAt)}</span>
                      <span className="tabular-nums text-[var(--color-muted)]">L {m.listening}</span>
                      <span className="tabular-nums text-[var(--color-muted)]">R {m.reading}</span>
                      <span className="tabular-nums font-semibold text-[var(--color-text)] w-10 text-right">
                        {m.overall}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {/* History list */}
            {history.length > 0 && (
            <Card>
              <p className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide mb-2">
                History
              </p>
              <ul className="flex flex-col divide-y divide-[var(--color-border)]">
                {history.map((a) => (
                  <li key={a.id}>
                    <button
                      type="button"
                      onClick={() => openDetail(a.id)}
                      className="w-full flex items-center gap-3 py-2.5 text-left min-h-11 hover:bg-[var(--color-surface-2)] rounded-[var(--radius-md)] px-2 -mx-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-600)]"
                    >
                      <span className="text-[var(--color-muted)]" aria-hidden="true">
                        {a.type === "writing" ? <PenLine size={16} /> : <Mic size={16} />}
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="block text-sm font-medium text-[var(--color-text)] capitalize">
                          {a.type} · {a.task}
                        </span>
                        <span className="block text-xs text-[var(--color-muted)]">{fmtDate(a.createdAt)}</span>
                      </span>
                      {a.cefr && <LevelChip band={a.cefr as CefrBand} />}
                      <span className="text-sm font-semibold tabular-nums text-[var(--color-text)] w-8 text-right">
                        {a.overall ?? "—"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
            )}
          </>
        )}
      </div>

      {/* Detail dialog — re-renders the saved feedback with the skill renderers */}
      <Dialog
        open={detail !== null || detailLoading}
        onClose={() => setDetail(null)}
        title={detail ? `${detail.type === "writing" ? "Writing" : "Speaking"} feedback` : "Loading…"}
      >
        <div className="max-h-[70vh] overflow-y-auto">
          {detailLoading && <p className="text-sm text-[var(--color-muted)]">Loading…</p>}
          {detail && detail.type === "writing" && <FeedbackView result={detail as WritingEval} />}
          {detail && detail.type === "speaking" && <SpeakingFeedback result={detail as SpeakingEval} />}
        </div>
      </Dialog>
    </main>
  );
};
