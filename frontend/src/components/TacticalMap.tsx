import React, { useState, useMemo, useEffect, useRef } from 'react';
import { EChartsReact } from 'react-echarts-library';
import type { EChartsOption } from 'echarts';
import './TacticalMap.css';

interface echartsPayload {
  x: number[];
  y: number[];
  data: Array<[x_index: number, y_index: number, total_pdf: number]>;
  max_pdf: number;
}

interface TacticalMapProps {
  configVersion: number;
}

const TacticalMap: React.FC<TacticalMapProps> = ({ configVersion }) => {
  const [payload] = useState<echartsPayload | null>(null);
  const [relSeconds, setRelSeconds] = useState<number | null>(null);
  const [timeRange] = useState<{
    min: number;
    max: number;
    step: number;
  }>({
    min: 0,
    max: 86100,
    step: 300,
  });
  const [options, setOptions] = useState<EChartsOption>({});
  const websocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // const ws = new WebSocket('ws://localhost:8000/ws/tactical-map/');
    // websocketRef.current = ws;
    // websocketRef.current.onmessage = (event) => {
    //   const data = JSON.parse(event.data);
    //   setPayload(data.payload);
    // };
    // return () => {
    //   if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
    //     websocketRef.current.close();
    //   }
    // };
  }, [configVersion]);

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
    <div className="tactical-map-container">
      <h2 className="tactical-title">Target Prediction Heatmap for Project Netfall</h2>

      <div className="tactical-slider-wrapper">
        <input
          type="range"
          className="tactical-slider"
          min={timeRange.min}
          max={timeRange.max}
          step={timeRange.step}
          value={relSeconds ?? 0}
          onChange={(e) => setRelSeconds(parseInt(e.target.value))}
        />
      </div>

      <p className="tactical-time-display">
        T+{' '}
        {Math.floor(relSeconds ? relSeconds / 3600 : 0)
          .toString()
          .padStart(2, '0')}
        :
        {Math.floor((relSeconds ? relSeconds % 3600 : 0) / 60)
          .toString()
          .padStart(2, '0')}
      </p>

      <div className="tactical-canvas-wrapper">
        {payload ? (
          <EChartsReact
            option={options}
            style={{ height: '100%', width: '100%' }}
            notMerge={true}
            lazyUpdate={true}
            theme={'dark'}
          />
        ) : (
          <div className="tactical-loading">
            <p>Initializing sensor array...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TacticalMap;
