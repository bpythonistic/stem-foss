import React, { useState, useEffect } from 'react';

interface styleInterface {
  container: React.CSSProperties;
  title: React.CSSProperties;
  slider: React.CSSProperties;
  updateButton: React.CSSProperties;
}

const styles: styleInterface = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    marginBottom: '10px',
  },
  slider: {
    width: '100%',
    marginBottom: '20px',
  },
  updateButton: {
    padding: '10px 20px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
};

const MapConfigUI: React.FC = () => {
  const [hoursBeforeNow, setHoursBeforeNow] = useState<number>(48);
  const [durationHours, setDurationHours] = useState<number>(24);
  const [timeSteps, setTimeSteps] = useState<number>(50);
  const [downsampleStep, setDownsampleStep] = useState<number>(4);

  const handleUpdateConfig = () => {
    // fetch('/configure_pdf_parameters/', {
    //   method: 'PUT',
    //   headers: {
    //     'Content-Type': 'application/json',
    //   },
    //   body: JSON.stringify({
    //     hours_before_now: hoursBeforeNow,
    //     duration_hours: durationHours,
    //     time_steps: timeSteps,
    //     downsample_step: downsampleStep,
    //   }),
    // });
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Tactical Map Configuration</h2>
      <label>
        Hours Before Now:
        <input
          type="range"
          min={0}
          max={168}
          step={4}
          value={hoursBeforeNow}
          onChange={(e) => setHoursBeforeNow(Number(e.target.value))}
          style={styles.slider}
        />
      </label>
      <label>
        Duration (Hours):
        <input
          type="range"
          min={1}
          max={24}
          step={1}
          value={durationHours}
          onChange={(e) => setDurationHours(Number(e.target.value))}
          style={styles.slider}
        />
      </label>
      <label>
        Time Steps:
        <input
          type="range"
          min={10}
          max={100}
          step={1}
          value={timeSteps}
          onChange={(e) => setTimeSteps(Number(e.target.value))}
          style={styles.slider}
        />
      </label>
      <label>
        Downsample Step:
        <input
          type="range"
          min={1}
          max={10}
          step={1}
          value={downsampleStep}
          onChange={(e) => setDownsampleStep(Number(e.target.value))}
          style={styles.slider}
        />
      </label>
      <button style={styles.updateButton} onClick={handleUpdateConfig}>
        Update Configuration
      </button>
    </div>
  );
};

export default MapConfigUI;
