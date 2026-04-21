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
}

const TacticalMap: React.FC<TacticalMapProps> = ({ configVersion }) => {
  const [payload, setPayload] = useState<EChartsPayload | null>(null);
  const [userName] = useState<string>('DefaultUser');
  const [userId, setUserId] = useState<string | null>(null);
  const [mapId, setMapId] = useState<string | null>(null);
  const [smallTargetId, setSmallTargetId] = useState<string | null>(null);
  const [mediumTargetId, setMediumTargetId] = useState<string | null>(null);
  const [largeTargetId, setLargeTargetId] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [selectedTargetClass, setSelectedTargetClass] = useState<TargetClass>(
    TargetClass.Small,
  );
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

  const handleTargetClass = (newClass: TargetClass) => {
    if (userId && mapId && smallTargetId && mediumTargetId && largeTargetId) {
      setSelectedTargetClass(newClass);
      switch (newClass) {
        case TargetClass.Small:
          setTargetId(smallTargetId);
          break;
        case TargetClass.Medium:
          setTargetId(mediumTargetId);
          break;
        case TargetClass.Large:
          setTargetId(largeTargetId);
          break;
        default:
          break;
      }
    }
  };

  useEffect(() => {
    // Initialize user, map, and target on component mount
    // This will be handled in a separate UI later
    // For now, we can just create a default user and map if they don't exist
    const initializeData = async () => {
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
          num_heat_points: 15,
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
    };
    initializeData().catch((error) => {
      console.error('Error initializing data:', error);
    });
  }, [configVersion]);

  useEffect(() => {
    let isMounted = true;

    const setupNewTargetConnection = async () => {
      if (!targetId) {
        return;
      }
      try {
        await saveTargetState(targetId, true);
      } catch (error) {
        console.error('Error saving target state on backend:', error);
        return; // Abort if the backend fails to prep the files
      }

      if (!isMounted) return;

      // 2. Close the old connection
      if (websocketRef.current) {
        websocketRef.current.close();
      }

      // 3. Open the new connection
      websocketRef.current = renderTacticalMapWebSocket(
        targetId,
        (raw_data) => {
          const data: EChartsPayload = raw_data ? JSON.parse(raw_data) : null;
          setPayload(data);
        },
        (error) => {
          console.error('WebSocket error:', error);
        },
      );

      // 4. Jumpstart the stream (Check if OPEN, otherwise wait for it)
      // Since the socket is asynchronous, we need to wait a tiny bit for it to open
      // before sending the current slider time.
      const jumpstartStream = () => {
        if (websocketRef.current?.readyState === WebSocket.OPEN) {
          websocketRef.current.send(JSON.stringify({ rel_seconds: relSeconds ?? 0 }));
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
  }, [targetId]);

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
          max: payload ? payload.max_val : 1,
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

      <div className="target-class-selector">
        <label htmlFor="target-class-select">Select Target Class: </label>
        <select
          id="target-class-select"
          value={selectedTargetClass}
          onChange={(e) => handleTargetClass(e.target.value as TargetClass)}
        >
          <option value={TargetClass.Small}>Small</option>
          <option value={TargetClass.Medium}>Medium</option>
          <option value={TargetClass.Large}>Large</option>
        </select>
      </div>

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
