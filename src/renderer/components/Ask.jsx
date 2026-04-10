import React, { useState } from 'react';

export default function Ask() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAsk = async () => {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setAnswer('');
    setError('');

    try {
      const result = await window.api.askQuestion(trimmed);
      setAnswer(result);
    } catch (err) {
      setError(err.message || 'Failed to get answer');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div className="ask-page">
      <h2 className="page-title">Ask</h2>
      <p className="page-subtitle">
        Ask a question about your notes. Claude will search your library and answer.
      </p>

      <div className="ask-input-wrapper">
        <textarea
          className="ask-input"
          placeholder="Ask anything about your notes..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
        />
        <button
          className="btn btn-primary"
          onClick={handleAsk}
          disabled={!question.trim() || loading}
        >
          {loading ? 'Thinking...' : 'Ask Claude'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading && (
        <div className="ask-loading">
          <div className="spinner" />
          <span>Searching notes and generating answer...</span>
        </div>
      )}

      {answer && (
        <div className="ask-answer">
          <h3>Answer</h3>
          <div className="answer-text">{answer}</div>
        </div>
      )}
    </div>
  );
}
