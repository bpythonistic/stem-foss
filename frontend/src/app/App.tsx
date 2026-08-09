import React, { useState } from 'react';
import TacticalMap from '../components/TacticalMap';
import MapConfigUI from '../components/MapConfigUI';
import Login from '../components/Login';
import { TargetClass } from './Api';
import './App.css';

interface Operator {
  id: string;
  name: string;
}

const TIME_RANGE = { min: 0, max: 86100, step: 300 };

const formatOffset = (seconds: number): string => {
  const h = Math.floor(seconds / 3600)
    .toString()
    .padStart(2, '0');
  const m = Math.floor((seconds % 3600) / 60)
    .toString()
    .padStart(2, '0');
  return `T+ ${h}:${m}`;
};

const App: React.FC = () => {
  const [operator, setOperator] = useState<Operator | null>(null);
  const [configVersion, setConfigVersion] = useState<number>(0);
  const [selectedTargetClass, setSelectedTargetClass] = useState<TargetClass>(
    TargetClass.Small,
  );
  const [relSeconds, setRelSeconds] = useState<number>(0);

  // Gate the app behind operator login until a user is resolved.
  if (!operator) {
    return <Login onLogin={setOperator} />;
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Project Netfall Central Command</h1>
        <div className="operator-bar">
          <span className="operator-name">Operator: {operator.name}</span>
          <button
            type="button"
            className="operator-logout"
            onClick={() => setOperator(null)}
          >
            Log Out
          </button>
        </div>
      </header>

      <main className="app-layout">
        <aside className="sidebar">
          <MapConfigUI onConfigChange={() => setConfigVersion((v) => v + 1)} />

          <div className="map-config-container">
            <h2 className="map-config-title">Intercept Controls</h2>

            <label className="map-config-label">
              Target Class
              <select
                className="tactical-selector"
                value={selectedTargetClass}
                onChange={(e) => setSelectedTargetClass(e.target.value as TargetClass)}
              >
                <option value={TargetClass.Small}>Small</option>
                <option value={TargetClass.Medium}>Medium</option>
                <option value={TargetClass.Large}>Large</option>
              </select>
            </label>

            <label className="map-config-label">
              Time Offset: {formatOffset(relSeconds)}
              <input
                type="range"
                className="map-config-slider"
                min={TIME_RANGE.min}
                max={TIME_RANGE.max}
                step={TIME_RANGE.step}
                value={relSeconds}
                onChange={(e) => setRelSeconds(parseInt(e.target.value))}
              />
            </label>
          </div>
        </aside>

        <section className="main-content">
          <TacticalMap
            userId={operator.id}
            configVersion={configVersion}
            selectedTargetClass={selectedTargetClass}
            relSeconds={relSeconds}
          />
        </section>
      </main>
    </div>
  );
};

export default App;
