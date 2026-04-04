import React, { useState } from 'react';

function extractTags(text) {
  const matches = text.match(/#(\w[\w-]*)/g);
  if (!matches) return [];
  return [...new Set(matches.map((m) => m.slice(1).toLowerCase()))];
}

export default function Capture({ onNoteCreated }) {
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState('');

  const handleSave = async () => {
    const trimmed = content.trim();
    if (!trimmed || saving) return;

    setSaving(true);
    try {
      const tags = extractTags(trimmed);
      await window.api.createNote(trimmed, tags);
      setContent('');
      setFlash('Note saved!');
      setTimeout(() => setFlash(''), 2000);
      if (onNoteCreated) onNoteCreated();
    } catch (err) {
      setFlash('Failed to save: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    }
  };

  const tags = extractTags(content);

  return (
    <div className="capture-page">
      <h2 className="page-title">Capture</h2>
      <p className="page-subtitle">Jot down a thought. Use #tag to add tags.</p>

      <div className="capture-input-wrapper">
        <textarea
          className="capture-input"
          placeholder="What's on your mind? Use #tag to categorize..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={4}
          autoFocus
        />
        <div className="capture-footer">
          <div className="capture-tags">
            {tags.map((tag) => (
              <span key={tag} className="tag-badge">{tag}</span>
            ))}
          </div>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!content.trim() || saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {flash && <div className="flash-message">{flash}</div>}

      <div className="capture-hint">
        Press <kbd>Enter</kbd> to save &middot; <kbd>Shift+Enter</kbd> for new line
      </div>
    </div>
  );
}
