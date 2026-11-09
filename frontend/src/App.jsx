import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowLeft, ArrowUpRight, Bot, Check, ChevronRight, CircleHelp,
  FileText, Gauge, Inbox, Layers3, Plus, RefreshCw, Search, Settings2,
  ShieldCheck, Sparkles, Upload, X, AlertCircle, Clock3
} from "lucide-react";
import "./index.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.message || `Request failed (${response.status})`);
  return data;
}

const NAV = [
  { id: "overview", label: "Overview", icon: Gauge },
  { id: "gaps", label: "Knowledge gaps", icon: CircleHelp },
  { id: "suggestions", label: "Suggestions", icon: Inbox },
  { id: "analysis", label: "Run analysis", icon: Activity },
];

function App() {
  const [agentId, setAgentId] = useState("demo-agent");
  const [agentDraft, setAgentDraft] = useState("demo-agent");
  const [gaps, setGaps] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [page, setPage] = useState("overview");
  const [selectedGap, setSelectedGap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  async function loadGaps(id = agentId) {
    if (!id.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api(`/v1/agents/${encodeURIComponent(id.trim())}/knowledge-gaps`);
      setGaps(Array.isArray(data) ? data : []);
      const suggestionData = await api("/v1/knowledge-suggestions");
      setSuggestions(Array.isArray(suggestionData) ? suggestionData : []);
      setAgentId(id.trim());
      setAgentDraft(id.trim());
      setSelectedGap(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadGaps("demo-agent"); }, []);

  const filteredGaps = useMemo(() => gaps.filter((gap) => {
    const matchesSearch = `${gap.title} ${gap.description} ${gap.category}`.toLowerCase().includes(search.toLowerCase());
    return matchesSearch && (statusFilter === "all" || gap.status === statusFilter);
  }), [gaps, search, statusFilter]);

  const pendingSuggestions = suggestions.filter((item) => item.status !== "approved" && item.status !== "rejected");
  const highPriority = gaps.filter((gap) => Number(gap.priority_score) >= 60).length;
  const totalEvidence = gaps.reduce((sum, gap) => sum + Number(gap.recurrence_count || 0), 0);

  function openGap(gap) {
    setSelectedGap(gap);
    setPage("gap-detail");
    setError("");
  }

  function go(next) {
    setPage(next);
    setSelectedGap(null);
    setError("");
  }

  return (
    <div className="shell">
      <aside className="rail">
        <button className="brand-mark" onClick={() => go("overview")} aria-label="Bolna home"><Bot size={22} strokeWidth={2.2} /></button>
        <div className="rail-rule" />
        <nav className="rail-nav" aria-label="Main navigation">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`rail-link ${page === id || (id === "gaps" && page === "gap-detail") ? "is-active" : ""}`} onClick={() => go(id)} title={label} aria-label={label}>
              <Icon size={19} strokeWidth={1.8} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="rail-bottom">
          <button className="rail-link" title="Workspace settings" aria-label="Workspace settings" onClick={() => go("settings")}><Settings2 size={19} /><span>Settings</span></button>
          <div className="profile-chip">B</div>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="workspace-switcher">
            <span className="workspace-symbol"><Layers3 size={16} /></span>
            <span className="workspace-name">Knowledge operations</span>
            <ChevronRight size={14} className="crumb-chevron" />
            <span className="workspace-context">{NAV.find((item) => item.id === page)?.label || (page === "gap-detail" ? "Gap details" : "Settings")}</span>
          </div>
          <div className="topbar-right">
            <div className="connection-state"><span className="connection-dot" /> API connected</div>
            <div className="agent-control">
              <Bot size={15} />
              <input aria-label="Agent ID" value={agentDraft} onChange={(event) => setAgentDraft(event.target.value)} onKeyDown={(event) => event.key === "Enter" && loadGaps(agentDraft)} />
              <button onClick={() => loadGaps(agentDraft)} disabled={loading} aria-label="Load agent"><RefreshCw size={14} /></button>
            </div>
          </div>
        </header>

        <main className="page-content">
          {error && <div className="notice notice-error"><AlertCircle size={16} />{error}<button onClick={() => setError("")} aria-label="Dismiss error"><X size={15} /></button></div>}
          {page === "overview" && <Overview gaps={gaps} highPriority={highPriority} totalEvidence={totalEvidence} pendingCount={pendingSuggestions.length} loading={loading} onOpenGaps={() => go("gaps")} onOpenAnalysis={() => go("analysis")} onOpenGap={openGap} />}
          {page === "gaps" && <GapList gaps={filteredGaps} total={gaps.length} loading={loading} search={search} setSearch={setSearch} statusFilter={statusFilter} setStatusFilter={setStatusFilter} onOpenGap={openGap} onRefresh={() => loadGaps()} />}
          {page === "gap-detail" && selectedGap && <GapDetail gap={selectedGap} onBack={() => go("gaps")} suggestions={suggestions.filter((item) => item.gap_id === selectedGap.id)} onCreated={(item) => setSuggestions((current) => [item, ...current])} onReviewed={(item) => setSuggestions((current) => current.map((old) => old.id === item.id ? { ...old, ...item } : old))} />}
          {page === "suggestions" && <SuggestionQueue suggestions={suggestions} gaps={gaps} onOpenGap={openGap} onReviewed={(item) => setSuggestions((current) => current.map((old) => old.id === item.id ? { ...old, ...item } : old))} />}
          {page === "analysis" && <Analysis agentId={agentId} onCompleted={() => loadGaps()} />}
          {page === "settings" && <Settings agentId={agentId} onAgentChange={(id) => { setAgentDraft(id); loadGaps(id); go("overview"); }} />}
        </main>
      </div>
    </div>
  );
}

function PageHeading({ eyebrow, title, description, actions }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{actions && <div className="heading-actions">{actions}</div>}</div>;
}

function Overview({ gaps, highPriority, totalEvidence, pendingCount, loading, onOpenGaps, onOpenAnalysis, onOpenGap }) {
  const topGaps = [...gaps].sort((a, b) => Number(b.priority_score) - Number(a.priority_score)).slice(0, 5);
  return <>
    <PageHeading eyebrow="WORKSPACE / OVERVIEW" title="Knowledge health" description="A clear view of what your voice agent knows, and where it needs help." actions={<button className="button button-primary" onClick={onOpenAnalysis}><Plus size={16} /> New analysis</button>} />
    <section className="overview-stats">
      <Stat label="Open knowledge gaps" value={gaps.filter((gap) => gap.status === "open").length} detail={`${gaps.length} identified in this agent`} icon={CircleHelp} />
      <Stat label="High priority" value={highPriority} detail="Score of 60 or above" icon={Activity} accent="warm" />
      <Stat label="Evidence occurrences" value={totalEvidence} detail="Across detected gaps" icon={FileText} />
      <Stat label="Pending suggestions" value={pendingCount} detail="Awaiting a review" icon={ShieldCheck} />
    </section>
    <section className="overview-main">
      <div className="section-card priority-section">
        <div className="section-title-row"><div><h2>Needs attention</h2><p>Highest scoring gaps, prioritized for review</p></div><button className="text-button" onClick={onOpenGaps}>All gaps <ArrowUpRight size={15} /></button></div>
        {loading ? <LoadingState label="Loading workspace" /> : topGaps.length ? <div className="priority-table">{topGaps.map((gap, index) => <button className="priority-row" key={gap.id} onClick={() => onOpenGap(gap)}><span className="row-index">{String(index + 1).padStart(2, "0")}</span><span className="row-main"><strong>{gap.title}</strong><small>{gap.category?.replaceAll("_", " ") || "Potential knowledge gap"}</small></span><span className={`score-pill ${scoreLevel(gap.priority_score)}`}>{gap.priority_score}</span><ChevronRight size={16} className="row-arrow" /></button>)}</div> : <EmptyState icon={CircleHelp} title="No gaps yet" body="Run an analysis on completed conversations to surface knowledge gaps." action={<button className="button button-secondary" onClick={onOpenAnalysis}>Run analysis</button>} />}
      </div>
      <div className="section-card workflow-card"><div className="workflow-kicker"><Sparkles size={15} /> WORKFLOW</div><h2>Close the knowledge loop</h2><p>Review evidence, propose a knowledge answer, and send it through approval.</p><div className="workflow-steps"><div><span>01</span><strong>Find a gap</strong><small>Identify repeated unanswered questions</small></div><div><span>02</span><strong>Draft an answer</strong><small>Turn evidence into useful content</small></div><div><span>03</span><strong>Review & approve</strong><small>Keep agent knowledge accountable</small></div></div><button className="button button-secondary button-wide" onClick={onOpenGaps}>Explore knowledge gaps <ArrowUpRight size={15} /></button></div>
    </section>
  </>;
}

function Stat({ label, value, detail, icon: Icon, accent }) {
  return <div className={`stat-card ${accent || ""}`}><div className="stat-card-top"><span>{label}</span><Icon size={17} /></div><strong>{value}</strong><small>{detail}</small></div>;
}

function GapList({ gaps, total, loading, search, setSearch, statusFilter, setStatusFilter, onOpenGap, onRefresh }) {
  return <>
    <PageHeading eyebrow="WORKSPACE / KNOWLEDGE GAPS" title="Knowledge gaps" description="Investigate unanswered questions and prioritize what your agent should learn." actions={<button className="button button-secondary" onClick={onRefresh} disabled={loading}><RefreshCw size={15} /> Refresh</button>} />
    <div className="list-toolbar"><div className="search-field"><Search size={16} /><input placeholder="Search questions, categories…" value={search} onChange={(event) => setSearch(event.target.value)} /></div><div className="filter-wrap"><span>State</span><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All states</option><option value="open">Open</option><option value="resolved">Resolved</option></select></div><span className="result-count">{gaps.length} of {total} gaps</span></div>
    <section className="section-card gap-table-card"><div className="table-header"><span>QUESTION / GAP</span><span>PRIORITY</span><span>OCCURRENCES</span><span>STATE</span><span /></div>
      {loading ? <LoadingState label="Loading gaps" /> : gaps.length ? gaps.map((gap) => <button className="gap-table-row" key={gap.id} onClick={() => onOpenGap(gap)}><span className="gap-title-cell"><span className="gap-type-icon"><CircleHelp size={16} /></span><span><strong>{gap.title}</strong><small>{gap.category?.replaceAll("_", " ") || "Potential knowledge gap"}</small></span></span><span><span className={`score-pill ${scoreLevel(gap.priority_score)}`}>{gap.priority_score}</span></span><span className="occurrence-cell"><Activity size={14} /> {gap.recurrence_count}</span><span><span className={`state-tag ${gap.status}`}>{gap.status}</span></span><ChevronRight size={16} className="row-arrow" /></button>) : <EmptyState icon={Search} title="No matching gaps" body="Try a different search or state filter." />}
    </section>
  </>;
}

function GapDetail({ gap, onBack, suggestions, onCreated, onReviewed }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [suggestionText, setSuggestionText] = useState("");
  const [creating, setCreating] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError(""); setDetails(null);
    api(`/v1/knowledge-gaps/${gap.id}`).then((data) => { if (!cancelled) setDetails(data); }).catch((err) => { if (!cancelled) setError(err.message); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [gap.id]);

  async function createSuggestion(event) {
    event.preventDefault();
    if (!suggestionText.trim()) return;
    setCreating(true); setError("");
    try {
      const item = await api(`/v1/knowledge-gaps/${gap.id}/suggestions`, { method: "POST", body: JSON.stringify({ suggested_content: suggestionText.trim() }) });
      onCreated(item); setSuggestionText("");
    } catch (err) { setError(err.message); } finally { setCreating(false); }
  }

  return <>
    <div className="back-row"><button className="back-button" onClick={onBack}><ArrowLeft size={16} /> Knowledge gaps</button><span className="detail-id">GAP / {gap.id.slice(0, 8).toUpperCase()}</span></div>
    <PageHeading eyebrow={`${gap.category?.replaceAll("_", " ") || "POTENTIAL KB GAP"} · ${gap.status?.toUpperCase() || "OPEN"}`} title={details?.title || gap.title} description={details?.description || gap.description} actions={<span className={`score-pill score-large ${scoreLevel(gap.priority_score)}`}>Priority {gap.priority_score}</span>} />
    {error && <div className="notice notice-error"><AlertCircle size={16} />{error}</div>}
    {loading ? <LoadingState label="Retrieving conversation evidence" /> : <div className="detail-layout">
      <div className="detail-primary"><div className="section-card evidence-card"><div className="section-title-row"><div><h2>Conversation evidence</h2><p>Source context behind this detected gap</p></div><span className="count-label">{details?.evidence?.length || 0} RECORDS</span></div>
        {details?.evidence?.length ? details.evidence.map((item, index) => (
          <article className="evidence-item" key={item.id}>
            <div className="evidence-meta">
              <span className="evidence-index">
                Evidence {String(index + 1).padStart(2, "0")}
              </span>
              <span className="conversation-id">
                Conversation ID <strong>{item.conversation_id}</strong>
              </span>
            </div>

            <div className="evidence-content">
              <section className="evidence-message customer-message">
                <div className="speaker-label">CUSTOMER QUESTION</div>
                <p>{item.question_text}</p>
              </section>

              {item.answer_text && (
                <section className="evidence-message agent-message">
                  <div className="speaker-label">AGENT RESPONSE</div>
                  <p>{item.answer_text}</p>
                </section>
              )}

              <section className="evidence-context">
                <div className="context-heading">
                  <FileText size={14} />
                  <span>Evidence context</span>
                </div>
                {(() => {
                  const parts = item.evidence_snippet?.split(/Agent response:/i);

                  if (parts?.length === 2) {
                    return (
                      <div className="evidence-context-lines">
                        <p>
                          <strong>Customer:</strong>{" "}
                          {parts[0].replace(/^Customer asked:\\s*/i, "").trim()}
                        </p>
                        <p>
                          <strong>Agent response:</strong>{" "}
                          {parts[1].trim()}
                        </p>
                      </div>
                    );
                  }

                  return <p>{item.evidence_snippet}</p>;
                })()}
              </section>
            </div>
          </article>
        )) : <EmptyState icon={FileText} title="No evidence attached" body="There are no conversation records available for this gap." />}
      </div></div>
      <aside className="detail-aside"><div className="section-card suggestion-compose"><div className="compose-icon"><Sparkles size={17} /></div><h2>Propose knowledge</h2><p>Draft an answer to fill this gap. Your proposal will enter the review workflow.</p><form onSubmit={createSuggestion}><label htmlFor="suggested-content">Suggested answer</label><textarea id="suggested-content" rows={8} value={suggestionText} onChange={(event) => setSuggestionText(event.target.value)} placeholder="Write a clear, accurate answer for your agent…" required /><div className="compose-footer"><span>{suggestionText.trim().length} characters</span><button className="button button-primary" type="submit" disabled={creating || !suggestionText.trim()}>{creating ? "Submitting…" : "Submit for review"}<ArrowUpRight size={15} /></button></div></form></div>
        <div className="section-card detail-facts"><h3>Gap properties</h3><Fact label="Priority score" value={gap.priority_score} /><Fact label="Occurrences" value={gap.recurrence_count} /><Fact label="Category" value={gap.category?.replaceAll("_", " ")} /><Fact label="Created" value={gap.created_at ? new Date(gap.created_at).toLocaleDateString() : "—"} /></div>
        <div className="section-card mini-suggestions"><div className="section-title-row"><h3>Submitted proposals</h3><span className="count-label">{suggestions.length}</span></div>{suggestions.length ? suggestions.map((item) => <div className="mini-suggestion" key={item.id}><p>{item.suggested_content}</p><span className={`state-tag ${item.status || "pending"}`}>{item.status || "pending"}</span></div>) : <p className="muted-copy">No proposals submitted for this gap yet.</p>}</div></aside>
    </div>}
  </>;
}

function Fact({ label, value }) { return <div className="fact-row"><span>{label}</span><strong>{value ?? "—"}</strong></div>; }

function SuggestionQueue({ suggestions, gaps, onOpenGap, onReviewed }) {
  const [feedback, setFeedback] = useState({});
  const [reviewing, setReviewing] = useState(null);
  const [filter, setFilter] = useState("pending");
  const items = suggestions.filter((item) => filter === "all" || item.status === filter || (filter === "pending" && (!item.status || item.status === "pending" || item.status === "pending_review")));
  async function review(item, status) {
    setReviewing(item.id);
    try {
      const updated = await api(`/v1/knowledge-suggestions/${item.id}`, { method: "PATCH", body: JSON.stringify({ status, reviewer_feedback: feedback[item.id]?.trim() || null }) });
      onReviewed({ ...item, ...updated });
    } catch (err) { window.alert(err.message); } finally { setReviewing(null); }
  }
  return <>
    <PageHeading eyebrow="WORKSPACE / SUGGESTIONS" title="Knowledge review" description="Evaluate proposed answers before they become part of your agent's knowledge." />
    <div className="list-toolbar"><div className="queue-tabs">{["pending", "approved", "rejected", "all"].map((state) => <button key={state} className={filter === state ? "active" : ""} onClick={() => setFilter(state)}>{state[0].toUpperCase() + state.slice(1)}</button>)}</div><span className="result-count">{items.length} proposals</span></div>
    <div className="review-list">{items.length ? items.map((item) => { const gap = gaps.find((entry) => entry.id === item.gap_id); return <article className="section-card review-card" key={item.id}><div className="review-card-head"><div><div className="eyebrow">{gap?.category?.replaceAll("_", " ") || "KNOWLEDGE PROPOSAL"}</div><h2>{gap?.title || `Gap ${item.gap_id.slice(0, 8)}`}</h2></div><span className={`state-tag ${item.status || "pending"}`}>{item.status || "pending"}</span></div><div className="proposal-content">{item.suggested_content}</div>{item.reviewer_feedback && <div className="review-feedback"><strong>Reviewer note</strong><p>{item.reviewer_feedback}</p></div>}{(!item.status || item.status === "pending" || item.status === "pending_review") && <div className="review-actions"><textarea rows={2} value={feedback[item.id] || ""} onChange={(event) => setFeedback((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="Optional reviewer note" /><div><button className="button button-secondary" onClick={() => gap && onOpenGap(gap)}><FileText size={15} /> View evidence</button><button className="button button-danger" disabled={reviewing === item.id} onClick={() => review(item, "rejected")}><X size={15} /> Reject</button><button className="button button-primary" disabled={reviewing === item.id} onClick={() => review(item, "approved")}><Check size={15} /> Approve</button></div></div>}</article>; }) : <EmptyState icon={Inbox} title="Nothing in this queue" body="Suggestions created from a gap detail view will appear here." />}</div>
  </>;
}

function Analysis({ agentId, onCompleted }) {
  const [raw, setRaw] = useState('[\n  { "conversation_id": "conv-001", "question": "What is your refund policy?", "answer": null },\n  { "conversation_id": "conv-002", "question": "How do I get a refund?", "answer": null }\n]');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault(); setError(""); setResult(null);
    let conversations;
    try { conversations = JSON.parse(raw); if (!Array.isArray(conversations)) throw new Error("Input must be a JSON array of conversations."); }
    catch (err) { setError(err.message); return; }
    setSubmitting(true);
    try { const data = await api(`/v1/agents/${encodeURIComponent(agentId)}/gap-analysis`, { method: "POST", body: JSON.stringify({ conversations }) }); setResult(data); onCompleted(); }
    catch (err) { setError(err.message); } finally { setSubmitting(false); }
  }
  return <>
    <PageHeading eyebrow="WORKSPACE / ANALYSIS" title="Analyze conversations" description="Submit completed voice-agent conversations to identify missing or incomplete knowledge." />
    <div className="analysis-layout"><section className="section-card analysis-form-card"><div className="analysis-step"><span>01</span><div><h2>Conversation input</h2><p>Provide conversation records in JSON format.</p></div></div><form onSubmit={submit}><label htmlFor="conversation-json">CONVERSATIONS JSON</label><textarea id="conversation-json" className="code-input" rows={15} value={raw} onChange={(event) => setRaw(event.target.value)} spellCheck="false" /><div className="analysis-form-footer"><span><FileText size={14} /> Expected: conversation_id, question, optional answer</span><button className="button button-primary" type="submit" disabled={submitting}>{submitting ? "Analyzing…" : "Run gap analysis"}<ArrowUpRight size={15} /></button></div></form>{error && <div className="notice notice-error"><AlertCircle size={16} />{error}</div>}{result && <div className="analysis-result"><div className="result-check"><Check size={18} /></div><div><strong>Analysis completed</strong><p>{result.total_conversations} conversations processed · Job {result.job_id}</p></div><span className="state-tag completed">{result.status}</span></div>}</section>
      <aside className="analysis-guide"><div className="guide-mark"><Upload size={19} /></div><h2>Prepare your data</h2><p>Analysis is based on completed conversation records. Unanswered questions help expose potential gaps.</p><div className="guide-list"><div><Check size={14} /><span>Use a unique conversation ID</span></div><div><Check size={14} /><span>Include the customer's question</span></div><div><Check size={14} /><span>Set answer to null if unanswered</span></div><div><Check size={14} /><span>Maximum 500 conversations per request</span></div></div><div className="guide-note"><ShieldCheck size={15} /> Gap detection and priority scoring are handled by the backend.</div></aside></div>
  </>;
}

function Settings({ agentId, onAgentChange }) {
  const [value, setValue] = useState(agentId);
  return <><PageHeading eyebrow="WORKSPACE / SETTINGS" title="Workspace settings" description="Manage the active voice agent for this knowledge workspace." /><section className="section-card settings-card"><div><h2>Active agent</h2><p>Knowledge gaps and analysis requests are scoped to this agent ID.</p></div><form onSubmit={(event) => { event.preventDefault(); onAgentChange(value.trim()); }}><label htmlFor="settings-agent">AGENT ID</label><input id="settings-agent" value={value} onChange={(event) => setValue(event.target.value)} required /><button className="button button-primary" type="submit">Apply agent <ArrowUpRight size={15} /></button></form></section></>;
}

function LoadingState({ label }) { return <div className="loading-state"><RefreshCw size={17} className="spin" /><span>{label}…</span></div>; }
function EmptyState({ icon: Icon, title, body, action }) { return <div className="empty-state"><div className="empty-icon"><Icon size={20} /></div><h3>{title}</h3><p>{body}</p>{action}</div>; }
function scoreLevel(score) { return Number(score) >= 60 ? "high" : Number(score) >= 30 ? "medium" : "low"; }

export default App;
