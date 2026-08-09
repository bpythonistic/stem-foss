const apiUrl = 'http://127.0.0.1:8000';
const defaultHeaders = {
  'Content-Type': 'application/json',
  'Access-Control-Allow-Origin': 'http://127.0.0.1:5173',
};

export const websocketUrl = 'ws://127.0.0.1:8000/ws/tactical_map/';

// export enum Category {
//   Monitor = 'Monitor',
//   Capture = 'Capture',
//   Refine = 'Refine',
//   Other = 'Other',
// }

// export enum Stat {
//   Resolution = 'Resolution',
//   NetSpeed = 'Net Speed',
//   NetSize = 'Net Size',
//   Stealth = 'Stealth',
// }

export enum TargetClass {
  Small = 'Small',
  Medium = 'Medium',
  Large = 'Large',
}

export enum LootDist {
  Uniform = 'Uniform',
  Normal = 'Normal',
  Gaussian = 'Gaussian',
}

interface GenericMessage {
  message: string;
}

interface ParamsState {
  start_time: string;
  duration_hours: number;
  time_steps: number;
  downsample_step: number;
}

interface User {
  id?: string;
  name: string;
  class_name: string;
}

// interface RPGClass {
//   id?: string;
//   name: string;
//   description: string;
//   trait_1: string;
//   trait_2: string | null;
//   trait_3: string | null;
// }

// interface Trait {
//   id?: string;
//   name: string;
//   description: string;
//   category: Category;
//   modifies: Stat;
//   multiplier: number;
//   offset: number;
// }

// interface Stats {
//   id?: string;
//   user_id: string;
//   stat_type: Stat;
//   stat_min: number;
//   stat_max: number;
//   base_value: number;
//   current_value: number;
// }

// interface Upgrade {
//   id?: string;
//   user_id: string;
//   name: string;
//   description: string;
//   cost: number;
//   effected_stat: Stat;
//   stat_multiplier: number;
//   stat_offset: number;
// }

interface Target {
  id?: string;
  user_id: string;
  map_id: string | null;
  name: string;
  description: string;
  category: TargetClass;
  top_speed: number;
  accel_max: number;
  decel_max: number;
  hitbox_size: number;
  loot_dist: LootDist;
  loot_min: number;
  loot_max: number;
  loot_mean: number | null;
  loot_stddev: number | null;
}

interface DefaultTargets {
  id?: string;
  user_id: string;
  small_target_id: string;
  medium_target_id: string;
  large_target_id: string;
}

interface Map {
  id?: string;
  user_id: string;
  name: string;
  description: string;
  map_size: number;
  samples: number;
  num_small_targets: number;
  num_medium_targets: number;
  num_large_targets: number;
  num_hot_spots: number;
}

export const fetchRoot = async (): Promise<{ message: string }> => {
  const response = await fetch(`${apiUrl}/`, {
    method: 'GET',
    headers: defaultHeaders,
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const createUser = async (user: Omit<User, 'id'>): Promise<User> => {
  const response = await fetch(`${apiUrl}/users/`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(user),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const fetchUser = async (userName: string): Promise<User> => {
  const response = await fetch(`${apiUrl}/users/${userName}`, {
    method: 'GET',
    headers: defaultHeaders,
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const createMap = async (map: Omit<Map, 'id'>): Promise<Map> => {
  const response = await fetch(`${apiUrl}/maps/`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(map),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const fetchMaps = async (): Promise<Map[]> => {
  const response = await fetch(`${apiUrl}/maps/`, {
    method: 'GET',
    headers: defaultHeaders,
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const createTarget = async (target: Omit<Target, 'id'>): Promise<Target> => {
  const response = await fetch(`${apiUrl}/targets/custom/`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(target),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const createDefaultTargets = async (
  userId: string,
  mapId: string,
): Promise<DefaultTargets> => {
  const response = await fetch(`${apiUrl}/targets/default/`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify({ user_id: userId, map_id: mapId }),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const fetchTargets = async (): Promise<Target[]> => {
  const response = await fetch(`${apiUrl}/targets/`, {
    method: 'GET',
    headers: defaultHeaders,
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const saveTargetState = async (
  targetSpecsId: string,
  loadFromDb: boolean = false,
): Promise<GenericMessage> => {
  const response = await fetch(
    `${apiUrl}/save_target_state/${targetSpecsId}?load_from_db=${loadFromDb}`,
    {
      method: 'PUT',
      headers: defaultHeaders,
    },
  );
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const clearCache = async (): Promise<GenericMessage> => {
  const response = await fetch(`${apiUrl}/clear_cache/`, {
    method: 'DELETE',
    headers: defaultHeaders,
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const updatePdfParameters = async (
  paramState: ParamsState,
): Promise<GenericMessage> => {
  const response = await fetch(`${apiUrl}/configure_pdf_parameters/`, {
    method: 'PUT',
    headers: defaultHeaders,
    body: JSON.stringify(paramState),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  return data;
};

export const renderTacticalMapWebSocket = (
  targetId: string,
  onData: (data: any) => void,
  onError: (error: any) => void,
): WebSocket => {
  const ws = new WebSocket(`${websocketUrl}${targetId}`);
  ws.onopen = () => {
    console.log('WebSocket connection established');
  };
  ws.onmessage = (event) => {
    try {
      onData(event.data);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      onError(error);
    }
  };
  ws.addEventListener('message', (event) => {
    try {
      ws.send(JSON.stringify(event.data));
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      onError(error);
    }
  });
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError(error);
  };
  ws.onclose = () => {
    console.log('WebSocket connection closed');
  };
  return ws;
};
