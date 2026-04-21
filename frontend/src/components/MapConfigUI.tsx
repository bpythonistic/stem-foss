import React, { useState } from 'react';
import './MapConfigUI.css';

import { updatePdfParameters } from '../app/Api';

interface MapConfigUIProps {
  onConfigChange: () => void;
}

const MapConfigUI: React.FC<MapConfigUIProps> = ({ onConfigChange }) => {
  const [hoursBeforeNow, setHoursBeforeNow] = useState<number>(-48);
  const [durationHours, setDurationHours] = useState<number>(24);
  const [timeSteps, setTimeSteps] = useState<number>(50);
  const [downsampleStep, setDownsampleStep] = useState<number>(4);

  const handleUpdateConfig = () => {
    const now = new Date();
    const startTime = new Date(now.getTime() + hoursBeforeNow * 60 * 60 * 1000);
    updatePdfParameters({
      start_time: startTime.toISOString(),
      duration_hours: durationHours,
      time_steps: timeSteps,
      downsample_step: downsampleStep,
    }).catch((error) => {
      console.error('Error updating PDF parameters:', error);
    });
    onConfigChange();
  };

  return (
    <div className="map-config-container">
      <h2 className="map-config-title">Data Collection Configuration</h2>

      <label className="map-config-label">
        First Timestamp (Hours Before Now): {hoursBeforeNow}
        <input
          type="range"
          className="map-config-slider"
          min={-168}
          max={-36}
          step={4}
          value={hoursBeforeNow}
          onChange={(e) => setHoursBeforeNow(Number(e.target.value))}
        />
      </label>

      <label className="map-config-label">
        Collection Duration (Hours): {durationHours}
        <input
          type="range"
          className="map-config-slider"
          min={4}
          max={24}
          step={2}
          value={durationHours}
          onChange={(e) => setDurationHours(Number(e.target.value))}
        />
      </label>

      <label className="map-config-label">
        Number of Time Samples: {timeSteps}
        <input
          type="range"
          className="map-config-slider"
          min={10}
          max={100}
          step={1}
          value={timeSteps}
          onChange={(e) => setTimeSteps(Number(e.target.value))}
        />
      </label>

      <label className="map-config-label">
        Downsample Step: {downsampleStep}
        <input
          type="range"
          className="map-config-slider"
          min={1}
          max={10}
          step={1}
          value={downsampleStep}
          onChange={(e) => setDownsampleStep(Number(e.target.value))}
        />
      </label>

      <button className="map-config-button" onClick={handleUpdateConfig}>
        Update Configuration
      </button>
    </div>
  );
};

export default MapConfigUI;
