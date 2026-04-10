import React, { useState, useEffect, useCallback } from 'react';

export default function Library() {
  const [notes, setNotes] = useState([]);
  const [tags, setTags] = useState([]);
  const [activeTag, setActiveTag] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [fetchedTags, fetchedNotes] = await Promise.all([
        window.api.getAllTags(),
        activeTag ? window.api.getNotesByTag(activeTag) : window.api.getAllNotes(),
      ]);
      setTags(fetchedTags);
      setNotes(fetchedNotes);
    } catch (err) {
      console.error('Failed to load notes:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTag]);

  useEffect(() => {
    loadData();
    const unsub = window.api.onNoteUpdated(() => loadData());
    return unsub;
  }, [loadData]);

  const handleDelete = async (id) => {
    await window.api.deleteNote(id);
    loadData();
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr + 'Z');
    return d.toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="library-page">
      <h2 className="page-title">Library</h2>

      <div className="tag-filter">
        <button
          className={`tag-filter-btn ${!activeTag ? 'active' : ''}`}
          onClick={() => setActiveTag(null)}
        >
          All
        </button>
        {tags.map((t) => (
          <button
            key={t.name}
            className={`tag-filter-btn ${activeTag === t.name ? 'active' : ''}`}
            onClick={() => setActiveTag(activeTag === t.name ? null : t.name)}
          >
            {t.name} <span className="tag-count">{t.count}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading">Loading...</div>
      ) : notes.length === 0 ? (
        <div className="empty-state">
          <p>No notes yet. Go to Capture to create one!</p>
        </div>
      ) : (
        <div className="notes-grid">
          {notes.map((note) => (
            <div key={note.id} className="note-card">
              <div className="note-content">{note.content}</div>
              {note.summary && (
                <div className="note-summary">{note.summary}</div>
              )}
              <div className="note-meta">
                <div className="note-tags">
                  {note.tags.map((tag) => (
                    <span
                      key={tag}
                      className="tag-badge clickable"
                      onClick={() => setActiveTag(tag)}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <span className="note-date">{formatDate(note.created_at)}</span>
              </div>
              <button
                className="note-delete"
                onClick={() => handleDelete(note.id)}
                title="Delete note"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
