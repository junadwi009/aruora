import React, { useState } from "react";
import { MessagesSquare, Send } from "lucide-react";
import { api } from "../../lib/api/client";
import type { SpeakingEval } from "../../lib/types";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Recorder } from "./Recorder";
import { SpeakingFeedback } from "./Speaking";

type Msg = { role: "assistant" | "user"; text: string };

const SCENARIOS: { name: string; opener: string }[] = [
  { name: "Hometown chat", opener: "Hi! Let's talk about where you're from. Where is your hometown, and what's it like?" },
  { name: "Job interview", opener: "Welcome. Thanks for coming in. To start, could you tell me a little about yourself?" },
  { name: "Coffee shop", opener: "Hi there! What can I get for you today — and is this your usual order?" },
  { name: "Travel plans", opener: "So, I heard you're planning a trip! Where are you thinking of going, and why there?" },
];

export const Roleplay: React.FC = () => {
  const [scenario, setScenario] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<SpeakingEval | null>(null);
  const [scoring, setScoring] = useState(false);

  const start = (name: string, opener: string) => {
    setScenario(name);
    setMessages([{ role: "assistant", text: opener }]);
    setFeedback(null);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || !scenario) return;
    const history = messages.map((m) => ({ role: m.role, text: m.text }));
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.speakingRoleplay({ scenario, history, userText: text });
      setMessages((m) => [...m, { role: "assistant", text: r.reply }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "(Sorry, I didn't catch that — could you say it again?)" }]);
    } finally {
      setBusy(false);
    }
  };

  const endConversation = async () => {
    if (!scenario) return;
    const userText = messages.filter((m) => m.role === "user").map((m) => m.text).join(" ");
    if (!userText) return;
    setScoring(true);
    try {
      setFeedback(await api.speakingEvaluate({ part: "roleplay", question: scenario, transcript: userText }));
    } finally {
      setScoring(false);
    }
  };

  return (
    <main className="flex-1 overflow-y-auto">
      <div className="sticky top-0 bg-[var(--color-surface)] border-b border-[var(--color-border)] px-4 py-3 z-10 flex items-center gap-2">
        <MessagesSquare size={18} className="text-[var(--color-primary-600)]" aria-hidden="true" />
        <h1 className="text-base font-semibold text-[var(--color-text)]">Speaking roleplay</h1>
      </div>

      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col gap-4">
        {!scenario ? (
          <Card className="flex flex-col gap-3">
            <p className="text-sm text-[var(--color-text)]">Pick a scenario to practise a real conversation. Speak or type your replies; finish to get examiner-style feedback.</p>
            <div className="grid grid-cols-2 gap-2">
              {SCENARIOS.map((s) => (
                <Button key={s.name} variant="secondary" onClick={() => start(s.name, s.opener)}>{s.name}</Button>
              ))}
            </div>
          </Card>
        ) : feedback ? (
          <>
            <SpeakingFeedback result={feedback} />
            <Button variant="secondary" onClick={() => { setScenario(null); setMessages([]); setFeedback(null); }}>
              ↩ New conversation
            </Button>
          </>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              {messages.map((m, i) => (
                <div key={i} className={`max-w-[85%] rounded-[var(--radius-lg)] px-3 py-2 text-sm ${
                  m.role === "assistant"
                    ? "self-start bg-[var(--color-surface-2)] text-[var(--color-text)]"
                    : "self-end bg-[var(--color-primary-600)] text-white"
                }`}>
                  {m.text}
                </div>
              ))}
              {busy && <div className="self-start text-xs text-[var(--color-muted)]">…</div>}
            </div>

            <Recorder onTranscript={(t) => setInput((p) => (p ? `${p} ${t}`.trim() : t))} />

            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Type or record your reply…"
                aria-label="Your reply"
                className="flex-1 min-h-11 px-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] text-sm text-[var(--color-text)]"
              />
              <Button onClick={send} disabled={!input.trim() || busy} aria-label="Send"><Send size={16} /></Button>
            </div>

            <Button variant="ghost" size="sm" onClick={endConversation} loading={scoring} className="self-end">
              End & get feedback
            </Button>
          </>
        )}
      </div>
    </main>
  );
};
