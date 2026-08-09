import React, { useState } from 'react';
import { createUser, fetchUser } from '../app/Api';
import './Login.css';

interface LoginProps {
  /** Called once a user has been resolved (fetched or newly created). */
  onLogin: (user: { id: string; name: string }) => void;
}

/**
 * Startup gate. Collects an operator callsign (no password) and either
 * fetches the matching user or registers a new one, then hands the
 * resolved user up to App.
 */
const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [callsign, setCallsign] = useState<string>('');
  const [isBusy, setIsBusy] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = callsign.trim();
    if (!name) {
      setError('Enter a callsign to continue.');
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      // Returning operators resolve directly; new ones are registered.
      let user = await fetchUser(name).catch(() => null);
      if (!user || !user.id) {
        await createUser({ name, class_name: 'DefaultClass' });
        user = await fetchUser(name);
      }
      if (!user || !user.id) {
        throw new Error('User ID not returned from API');
      }
      onLogin({ id: user.id, name: user.name });
    } catch (err) {
      console.error('Login failed:', err);
      setError('Unable to reach Command. Is the backend running?');
      setIsBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="login-panel" onSubmit={handleSubmit}>
        <h1 className="login-title">Project Netfall</h1>
        <p className="login-subtitle">Operator Authentication</p>

        <label className="login-label" htmlFor="callsign">
          Callsign
        </label>
        <input
          id="callsign"
          className="login-input"
          type="text"
          value={callsign}
          onChange={(e) => setCallsign(e.target.value)}
          placeholder="e.g. Nightjar"
          autoFocus
          disabled={isBusy}
          autoComplete="off"
        />

        {error && <p className="login-error">{error}</p>}

        <button className="login-button" type="submit" disabled={isBusy}>
          {isBusy ? 'Establishing Link…' : 'Enter Command'}
        </button>

        <p className="login-hint">
          New operators are registered automatically. No password required.
        </p>
      </form>
    </div>
  );
};

export default Login;
