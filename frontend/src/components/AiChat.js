import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const WELCOME = {
  role: 'assistant',
  content: "Hi, I'm BrokerOS AI. Ask me anything about your pipeline, lender criteria, or mortgage processes.",
  isWelcome: true,
};

export function AiChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [welcomed, setWelcomed] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Show welcome message on first open only
  useEffect(() => {
    if (isOpen && !welcomed) {
      setMessages([WELCOME]);
      setWelcomed(true);
    }
  }, [isOpen, welcomed]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    // Build API history — exclude welcome message, include all prior real turns
    const apiHistory = messages
      .filter(m => !m.isWelcome)
      .map(({ role, content }) => ({ role, content }));

    try {
      const { data } = await axios.post(
        `${API}/ai/chat`,
        { message: text, conversation_history: apiHistory },
        { withCredentials: true }
      );
      setMessages(prev => [...prev, { role: 'assistant', content: data.data.response }]);
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'error', content: "Sorry, I couldn't process that — please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* ── Chat Panel ─────────────────────────────────── */}
      {isOpen && (
        <div
          data-testid="ai-chat-panel"
          style={{
            position: 'fixed',
            bottom: '96px',
            right: '24px',
            width: '380px',
            height: '520px',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
            zIndex: 8000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div style={{
            backgroundColor: '#0A2342',
            padding: '0 16px',
            height: '48px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
          }}>
            <span style={{ color: 'white', fontSize: '14px', fontWeight: '700' }}>BrokerOS AI</span>
            <button
              onClick={() => setIsOpen(false)}
              data-testid="ai-chat-close"
              aria-label="Close chat"
              style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '22px', lineHeight: 1, padding: '0 2px' }}
            >
              ×
            </button>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
                data-testid={msg.role === 'user' ? `chat-user-msg-${idx}` : `chat-assistant-msg-${idx}`}
              >
                <div style={{
                  maxWidth: '80%',
                  padding: '10px 12px',
                  borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                  backgroundColor: msg.role === 'user' ? '#0A2342' : msg.role === 'error' ? '#FEF2F2' : '#F3F4F6',
                  color: msg.role === 'user' ? 'white' : '#111827',
                  fontSize: '14px',
                  lineHeight: '1.5',
                  border: msg.role === 'error' ? '1px solid #EF4444' : 'none',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {msg.content}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }} data-testid="ai-chat-typing">
                <div style={{
                  padding: '10px 14px',
                  borderRadius: '12px 12px 12px 2px',
                  backgroundColor: '#F3F4F6',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}>
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div style={{
            borderTop: '1px solid #E5E7EB',
            padding: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'white',
            flexShrink: 0,
          }}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything…"
              disabled={isLoading}
              data-testid="ai-chat-input"
              style={{
                flex: 1,
                border: 'none',
                outline: 'none',
                fontSize: '14px',
                padding: '4px 0',
                backgroundColor: 'transparent',
                color: '#111827',
              }}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              data-testid="ai-chat-send"
              aria-label="Send message"
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '6px',
                backgroundColor: isLoading || !input.trim() ? '#D1D5DB' : '#0E9F6E',
                border: 'none',
                cursor: isLoading || !input.trim() ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                transition: 'background-color 0.15s',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* ── Floating Button ─────────────────────────────── */}
      <button
        onClick={() => setIsOpen(prev => !prev)}
        data-testid="ai-chat-toggle"
        aria-label={isOpen ? 'Close AI assistant' : 'Open AI assistant'}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: '#0E9F6E',
          border: 'none',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 8000,
          transition: 'background-color 0.15s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#0B8A5E'; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#0E9F6E'; }}
      >
        {isOpen ? (
          /* × close icon */
          <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
          </svg>
        ) : (
          /* Chat bubble icon */
          <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
          </svg>
        )}
      </button>
    </>
  );
}
