import React, { useState } from 'react';
import TacticalMap from '../components/TacticalMap';
import MapConfigUI from '../components/MapConfigUI';
import './App.css';

const App: React.FC = () => {
  const [configVersion, setConfigVersion] = useState<number>(0);

  const handleConfigChange = () => {
    setConfigVersion((prevVersion) => prevVersion + 1);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Project Netfall Central Command</h1>
      </header>

      <main className="app-layout">
        <aside className="sidebar">
          <MapConfigUI onConfigChange={handleConfigChange} />
        </aside>

        <section className="main-content">
          <TacticalMap configVersion={configVersion} />
        </section>
      </main>
    </div>
  );
};

export default App;
