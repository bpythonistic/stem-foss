import React from 'react';

import TacticalMap from '../components/TacticalMap';

export default function MyApp() {
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <h1 className="text-2xl font-bold mb-4">Welcome to Project Netfall!</h1>
      <TacticalMap />
    </div>
  );
}
