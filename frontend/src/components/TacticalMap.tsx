import React, { useState, useEffect, useRef } from 'react';
import { EChartsReact } from 'react-echarts-library';
import type { EChartsOption } from 'echarts';
import {
  TargetClass,
  createUser,
  fetchUser,
  fetchMaps,
  fetchTargets,
  createMap,
  createDefaultTargets,
  saveTargetState,
  renderTacticalMapWebSocket,
} from '../app/Api';
import './TacticalMap.css';

interface EChartsPayload {
  x: number[];
  y: number[];
  data: number[][];
  max_val: number;
}

interface TacticalMapProps {
  configVersion: number;
  selectedTargetClass: TargetClass;
  relSeconds: number;
}

/** Returns the set of axis indices that are closest to each multiple of `step`. */
const tickIndices = (values: number[], step = 10): Set<number> => {
  const result = new Set<number>();
  const max = Math.ceil(Math.max(...values) / step) * step;
  for (let m = Math.floor(Math.min(...values) / step) * step; m <= max; m += step) {
    let best = 0;
    let bestDist = Infinity;
    values.forEach((v, i) => {
      const d = Math.abs(v - m);
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    });
    result.add(best);
  }
  return result;
};

const TacticalMap: React.FC<TacticalMapProps> = ({
  configVersion,
  selectedTargetClass,
  relSeconds,
}) => {
  const [payload, setPayload] = useState<EChartsPayload | null>(null);
  const [userName] = useState<string>('DefaultUser');
  const [userId, setUserId] = useState<string | null>(null);
  const [mapId, setMapId] = useState<string | null>(null);
  const [smallTargetId, setSmallTargetId] = useState<string | null>(null);
  const [mediumTargetId, setMediumTargetId] = useState<string | null>(null);
  const [largeTargetId, setLargeTargetId] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadingMessage, setLoadingMessage] = useState<string>(
    'Initializing sensor array...',
  );
  const [wsVersion, setWsVersion] = useState<number>(0);
  const [options, setOptions] = useState<EChartsOption>({});
  const websocketRef = useRef<WebSocket | null>(null);

  // When the user picks a different target class from the sidebar, switch targets.
  useEffect(() => {
    if (!smallTargetId || !mediumTargetId || !largeTargetId) return;
    setIsLoading(true);
    setLoadingMessage('Recalibrating sensors...');
    switch (selectedTargetClass) {
      case TargetClass.Small:
        setTargetId(smallTargetId);
        break;
      case TargetClass.Medium:
        setTargetId(mediumTargetId);
        break;
      case TargetClass.Large:
        setTargetId(largeTargetId);
        break;
    }
  }, [selectedTargetClass]);

  useEffect(() => {
    const initializeData = async () => {
      setIsLoading(true);
      setLoadingMessage('Initializing sensor array...');
      if (!userId) {
        const existingUser = await fetchUser(userName).catch(() => null);
        if (existingUser && existingUser.id) {
          setUserId(existingUser.id);
        } else {
          await createUser({ name: userName, class_name: 'DefaultClass' });
          const newUser = await fetchUser(userName);
          if (!newUser || !newUser.id) {
            throw new Error('User ID not returned from API');
          }
          setUserId(newUser.id);
        }
      }
      const targets = await fetchTargets().catch(() => []);
      const selectedTarget = targets.find((t) => t.category === selectedTargetClass);
      let selectedTargetId = selectedTarget ? selectedTarget.id : null;
      if (!selectedTargetId) {
        const map = await createMap({
          user_id: userId || '',
          name: 'Default Map',
          description: 'A default map for testing',
          map_size: 200,
          samples: 200,
          num_small_targets: 15,
          num_medium_targets: 10,
          num_large_targets: 5,
          num_hot_spots: 15,
        });
        const newMap = await fetchMaps().then((maps) =>
          maps.find((m) => m.id === map.id),
        );
        if (!newMap || !newMap.id) {
          throw new Error('Map ID not returned from API');
        }
        const defaultTargets = await createDefaultTargets(
          userId || '',
          newMap.id || '',
        ).catch(() => null);
        if (!defaultTargets || !defaultTargets.small_target_id) {
          throw new Error('Small target ID not returned from API');
        }
        setSmallTargetId(defaultTargets.small_target_id);
        setMediumTargetId(defaultTargets.medium_target_id);
        setLargeTargetId(defaultTargets.large_target_id);
        switch (selectedTargetClass) {
          case TargetClass.Small:
            selectedTargetId = defaultTargets.small_target_id;
            break;
          case TargetClass.Medium:
            selectedTargetId = defaultTargets.medium_target_id;
            break;
          case TargetClass.Large:
            selectedTargetId = defaultTargets.large_target_id;
            break;
          default:
            break;
        }
      }
      if (!selectedTargetId) {
        throw new Error('No target ID available');
      }
      const maps = await fetchMaps().catch(() => []);
      const selectedMap = maps.find((m) => m.id === selectedTarget?.map_id);
      if (!selectedMap) {
        throw new Error('Map not found for target');
      }
      setMapId(selectedMap.id || null);
      setSmallTargetId(
        targets.find((t) => t.category === TargetClass.Small)?.id || null,
      );
      setMediumTargetId(
        targets.find((t) => t.category === TargetClass.Medium)?.id || null,
      );
      setLargeTargetId(
        targets.find((t) => t.category === TargetClass.Large)?.id || null,
      );
      if (userId && mapId && selectedTargetId) {
        await saveTargetState(selectedTargetId, true).catch((error) => {
          console.error('Error saving target state:', error);
        });
      }
      setTargetId(selectedTargetId);
      setWsVersion((v) => v + 1);
    };
    initializeData().catch((error) => {
      console.error('Error initializing data:', error);
    });
  }, [configVersion]);

  useEffect(() => {
    let isMounted = true;

    const setupNewTargetConnection = async () => {
      if (!targetId) return;
      try {
        await saveTargetState(targetId, true);
      } catch (error) {
        console.error('Error saving target state on backend:', error);
        return;
      }

      if (!isMounted) return;

      if (websocketRef.current) {
        websocketRef.current.close();
      }

      websocketRef.current = renderTacticalMapWebSocket(
        targetId,
        (raw_data) => {
          const data: EChartsPayload = raw_data ? JSON.parse(raw_data) : null;
          setPayload(data);
          setIsLoading(false);
        },
        (error) => {
          console.error('WebSocket error:', error);
        },
      );

      const jumpstartStream = () => {
        if (websocketRef.current?.readyState === WebSocket.OPEN) {
          websocketRef.current.send(JSON.stringify({ rel_seconds: relSeconds }));
        } else {
          setTimeout(jumpstartStream, 50);
        }
      };
      jumpstartStream();
    };
    setupNewTargetConnection();
    return () => {
      isMounted = false;
      websocketRef.current?.close();
    };
  }, [targetId, wsVersion]);

  useEffect(() => {
    websocketRef.current?.send(JSON.stringify({ rel_seconds: relSeconds }));
  }, [relSeconds]);

  useEffect(() => {
    if (payload) {
      console.log('Updating chart options with new payload');
      const newOptions: EChartsOption = {
        title: {
          text: 'Tactical Map',
        },
        tooltip: {
          trigger: 'item',
          formatter: (params: unknown) => {
            const p = params as { value: [number, number, number] };
            if (!p.value || p.value[2] === 0) return '';
            return `P(intercept): ${(p.value[2] * 100).toFixed(2)}%`;
          },
        },
        xAxis: (() => {
          const xt = tickIndices(payload.x);
          return {
            type: 'category' as const,
            data: payload.x,
            axisLabel: {
              interval: (i: number) => xt.has(i),
              formatter: (v: string) => String(Math.round(parseFloat(v) / 10) * 10),
            },
            axisTick: { interval: (i: number) => xt.has(i) },
            splitLine: {
              show: true,
              interval: (i: number) => xt.has(i),
              lineStyle: { color: 'rgba(255,255,255,0.07)' },
            },
          };
        })(),
        yAxis: (() => {
          const yt = tickIndices(payload.y);
          return {
            type: 'category' as const,
            data: payload.y,
            axisLabel: {
              interval: (i: number) => yt.has(i),
              formatter: (v: string) => String(Math.round(parseFloat(v) / 10) * 10),
            },
            axisTick: { interval: (i: number) => yt.has(i) },
            splitLine: {
              show: true,
              interval: (i: number) => yt.has(i),
              lineStyle: { color: 'rgba(255,255,255,0.07)' },
            },
          };
        })(),
        visualMap: {
          min: 0,
          max: payload.max_val,
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
            data: payload.data,
            emphasis: {
              itemStyle: {
                borderColor: '#333',
                borderWidth: 1,
              },
            },
            progressive: 0,
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

      <div className="tactical-canvas-wrapper">
        {payload && (
          <EChartsReact
            option={options}
            style={{ height: '100%', width: '100%' }}
            notMerge={true}
            lazyUpdate={true}
            theme={'dark'}
          />
        )}
        {isLoading && !payload && (
          <div className="tactical-loading">
            <p>{loadingMessage}</p>
          </div>
        )}
        {isLoading && payload && (
          <div className="tactical-loading-overlay">
            <div className="tactical-spinner" />
            <p className="tactical-loading-text">{loadingMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TacticalMap;
