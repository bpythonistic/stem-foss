import React, { useState, useMemo, useEffect, useRef } from 'react';
import { EChartsReact } from 'react-echarts-library';
import type { EChartsOption } from 'echarts';

interface echartsPayload {
  x: number[];
  y: number[];
  data: Array<[x_index: number, y_index: number, total_pdf: number]>;
  max_pdf: number;
}

interface styleInterface {
  container: React.CSSProperties;
  title: React.CSSProperties;
  slider: React.CSSProperties;
  radio: React.CSSProperties;
  chart: React.CSSProperties;
}

const styles: styleInterface = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '20px',
    backgroundColor: '#1e1e1e',
    borderRadius: '8px',
    width: '100%',
    height: '100%',
  },
  title: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: '20px',
  },
  slider: {
    width: '80%',
    marginBottom: '20px',
  },
  radio: {
    margin: '0 10px',
  },
  chart: {
    width: '100%',
    height: '400px',
  },
};

const TacticalMap: React.FC = () => {
  const [payload, setPayload] = useState<echartsPayload | null>(null);
  const [relSeconds, setRelSeconds] = useState<number | null>(null);
  const [theme, setTheme] = useState<string>('dark');
  const [options, setOptions] = useState<EChartsOption>({});
  const websocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/tactical-map/');
    websocketRef.current = ws;
    websocketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setPayload(data.payload);
    };

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    websocketRef.current?.send(JSON.stringify({ rel_seconds: relSeconds }));
  }, [relSeconds]);

  useMemo(() => {
    if (payload) {
      const newOptions: EChartsOption = {
        title: {
          text: 'Tactical Map',
        },
        tooltip: {
          trigger: 'axis',
        },
        xAxis: {
          type: 'category',
          data: payload ? payload.x : [],
        },
        yAxis: {
          type: 'category',
          data: payload ? payload.y : [],
        },
        visualMap: {
          min: 0,
          max: payload ? payload.max_pdf : 1,
          calculable: true,
          realtime: false,
          inRange: {
            color: [
              '#313695',
              '#4575b4',
              '#74add1',
              '#abd9e9',
              '#e0f3f8',
              '#ffffbf',
              '#fee090',
              '#fdae61',
              '#f46d43',
              '#d73027',
              '#a50026',
            ],
          },
        },
        series: [
          {
            name: 'Tactical Map',
            type: 'heatmap',
            data: payload ? payload.data : [],
            emphasis: {
              itemStyle: {
                borderColor: '#333',
                borderWidth: 1,
              },
            },
            progressive: 1000,
            animation: false,
          },
        ],
      };
      setOptions(newOptions);
    } else {
      setOptions({});
    }
  }, [payload]);

  return (
    <div style={styles.container}>
      <div style={styles.title}>Tactical Map</div>
      <input
        type="radio"
        style={styles.radio}
        name="theme"
        value="dark"
        checked={theme === 'dark'}
        onChange={() => setTheme('dark')}
      />
      <input
        type="radio"
        style={styles.radio}
        name="theme"
        value="light"
        checked={theme === 'light'}
        onChange={() => setTheme('light')}
      />
      <input
        type="range"
        style={styles.slider}
        min={0}
        max={86400}
        step={300}
        value={relSeconds ?? 0}
        onChange={(e) => setRelSeconds(parseInt(e.target.value))}
      />
      <EChartsReact
        option={options}
        notMerge={true}
        lazyUpdate={true}
        style={styles.chart}
        showLoading={payload === null}
        loadingOption={{ text: 'Loading tactical map...' }}
        theme={theme}
      />
    </div>
  );
};

export default TacticalMap;
