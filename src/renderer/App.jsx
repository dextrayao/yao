import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Capture from './components/Capture';
import Library from './components/Library';
import Ask from './components/Ask';
import Settings from './components/Settings';

const PAGES = {
  capture: Capture,
  library: Library,
  ask: Ask,
  settings: Settings,
};

export default function App() {
  const [activePage, setActivePage] = useState('capture');
  const [refreshKey, setRefreshKey] = useState(0);

  const PageComponent = PAGES[activePage];

  const handleNoteCreated = () => {
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="app-layout">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="main-content">
        <PageComponent
          key={`${activePage}-${refreshKey}`}
          onNoteCreated={handleNoteCreated}
        />
      </main>
    </div>
  );
}
