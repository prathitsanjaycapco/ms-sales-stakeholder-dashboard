import React, { useEffect, useRef, useState } from "react";
import { Bot, ChevronRight, Clock3, ExternalLink, MessageCircle, Plus, Send, ShieldCheck, Sparkles, Trash2, X } from "lucide-react";
import { api } from "./api";

const suggestions = [
  "Summarize the account’s current performance",
  "Which relationships need attention?",
  "What are the highest-value opportunities?",
  "Which projects or critical items are at risk?",
];

function Citation({ citation, onNavigate }) {
  const canNavigate = citation.navigation && citation.navigation.type;
  const content = <><span>{citation.title}</span><small>{citation.source_type.replaceAll("_", " ")}{citation.pod ? ` · ${citation.pod}` : ""}</small></>;
  if (canNavigate) return <button className="assistant-citation" onClick={() => onNavigate(citation.navigation)}>{content}<ChevronRight /></button>;
  if (citation.url) return <a className="assistant-citation" href={citation.url} target="_blank" rel="noreferrer">{content}<ExternalLink /></a>;
  return <div className="assistant-citation static">{content}</div>;
}

export default function AccountAssistant({ context, onNavigate }) {
  const [open, setOpen] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bodyRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    let active = true;
    api.getAssistantConversations().then(async (rows) => {
      if (!active) return;
      setConversations(rows);
      if (!conversationId && rows.length) {
        const detail = await api.getAssistantConversation(rows[0].id);
        if (active) { setConversationId(detail.id); setMessages(detail.messages); }
      }
    }).catch(() => active && setError("Conversation history is temporarily unavailable."));
    return () => { active = false; };
  }, [open]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => event.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [open]);

  const newConversation = () => {
    setConversationId(null);
    setMessages([]);
    setHistoryOpen(false);
    setError("");
  };

  const loadConversation = async (id) => {
    setLoading(true);
    setError("");
    try {
      const detail = await api.getAssistantConversation(id);
      setConversationId(detail.id);
      setMessages(detail.messages);
      setHistoryOpen(false);
    } catch (requestError) {
      setError(requestError.message || "Conversation could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  const removeConversation = async (id) => {
    setError("");
    try {
      await api.deleteAssistantConversation(id);
      const remaining = conversations.filter((item) => item.id !== id);
      setConversations(remaining);
      if (conversationId === id) newConversation();
    } catch (requestError) {
      setError(requestError.message || "Conversation could not be removed.");
    }
  };

  const send = async (question = value) => {
    const message = question.trim();
    if (!message || loading) return;
    setValue("");
    setError("");
    const optimistic = { id: `local-${Date.now()}`, role: "user", content: message, citations: [] };
    setMessages((rows) => [...rows, optimistic]);
    setLoading(true);
    try {
      const response = await api.askAssistant(message, conversationId, context);
      setConversationId(response.conversation_id);
      setMessages((rows) => [...rows, response.message]);
      api.getAssistantConversations().then(setConversations).catch(() => {});
    } catch (requestError) {
      setError(requestError.message || "The account assistant could not answer right now.");
    } finally {
      setLoading(false);
    }
  };

  return <>
    <button className={`assistant-launcher ${open ? "active" : ""}`} onClick={() => setOpen(!open)} aria-label="Ask the Morgan Stanley account assistant" title="Ask account AI">
      {open ? <X /> : <MessageCircle />}<span>Ask account AI</span>
    </button>
    {open && <aside className="account-assistant" role="dialog" aria-label="Morgan Stanley account assistant">
      <header>
        <div className="assistant-mark"><Sparkles /></div>
        <div><span>CAPCO ACCOUNT INTELLIGENCE</span><h2>Ask Morgan Stanley AI</h2></div>
        <button onClick={newConversation} title="New conversation" aria-label="New conversation"><Plus /></button>
        <button onClick={() => setOpen(false)} title="Close assistant" aria-label="Close assistant"><X /></button>
      </header>
      <div className="assistant-context"><ShieldCheck /><span>Grounded in approved account records</span><em>{context.pod || "All"} · {context.section || "Account"}</em></div>
      <div className="assistant-history-control">
        <button onClick={() => setHistoryOpen(!historyOpen)}><Clock3 /> History <span>{conversations.length}</span></button>
        {historyOpen && <div className="assistant-history-list">
          {conversations.map((item) => <div key={item.id} className={item.id === conversationId ? "active" : ""}><button onClick={() => loadConversation(item.id)}><b>{item.title}</b><small>{new Date(item.updated_at).toLocaleString()}</small></button><button onClick={() => removeConversation(item.id)} title="Delete conversation" aria-label={`Delete ${item.title}`}><Trash2 /></button></div>)}
          {!conversations.length && <p>No previous conversations.</p>}
        </div>}
      </div>
      <div className="assistant-messages" ref={bodyRef}>
        {!messages.length && <section className="assistant-welcome">
          <Bot /><h3>What do you need to know?</h3>
          <p>I retrieve from PostgreSQL-backed account records and indexed document content. Answers stay within the Morgan Stanley account and include evidence.</p>
          <div>{suggestions.map((item) => <button key={item} onClick={() => send(item)}>{item}<ChevronRight /></button>)}</div>
        </section>}
        {messages.map((message) => <article key={message.id} className={`assistant-message ${message.role}`}>
          <div className="assistant-message-label">{message.role === "assistant" ? <><Sparkles /> Account AI</> : "You"}</div>
          <p>{message.content}</p>
          {!!message.citations?.length && <details><summary>{message.citations.length} account source{message.citations.length === 1 ? "" : "s"}</summary><div>{message.citations.map((citation) => <Citation key={citation.id} citation={citation} onNavigate={onNavigate} />)}</div></details>}
        </article>)}
        {loading && <article className="assistant-message assistant thinking"><div className="assistant-message-label"><Sparkles /> Account AI</div><p><i /><i /><i /> Retrieving account evidence…</p></article>}
        {error && <div className="assistant-error">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
      </div>
      <form className="assistant-composer" onSubmit={(event) => { event.preventDefault(); send(); }}>
        <textarea autoFocus rows="2" value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Ask about stakeholders, meetings, pipeline, delivery, workforce, or documents…" />
        <button disabled={loading || value.trim().length < 2} aria-label="Send question"><Send /></button>
        <small>Account data only · Verify commercial decisions against cited records</small>
      </form>
    </aside>}
  </>;
}
