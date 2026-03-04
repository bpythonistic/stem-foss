import React from 'react';
import { createRoot } from 'react-dom/client';
import MyApp from './App';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MyApp />
  </React.StrictMode>,
);
