import React, { useState, useEffect } from 'react';

export default function Settings() {
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    window.api.getSetting('anthropic_api_key').then((val) => {
      if (val) setApiKey(val);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    await window.api.setSetting('anthropic_api_key', apiKey.trim());
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="settings-page">
      <h2 className="page-title">Settings</h2>

      <div className="settings-section">
        <label className="settings-label" htmlFor="api-key">
          Anthropic API Key
        </label>
        <p className="settings-hint">
          Required for AI-powered summaries, auto-tagging, and Ask features.
        </p>
        <input
          id="api-key"
          type="password"
          className="settings-input"
          placeholder="sk-ant-..."
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={!apiKey.trim()}
        >
          Save
        </button>
        {saved && <span className="settings-saved">Saved!</span>}
      </div>
    </div>
  );
}
