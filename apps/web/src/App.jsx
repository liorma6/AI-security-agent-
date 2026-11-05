import { useEffect, useState } from 'react';

export default function App() {
  const [connection, setConnection] = useState('loading');

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    fetch('/api/health', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Server unavailable');
        const health = await response.json();
        if (health.service !== 'api' || health.status !== 'ok') throw new Error('Invalid health response');
        if (active) setConnection('connected');
      })
      .catch(() => { if (active) setConnection('unavailable'); })
      .finally(() => clearTimeout(timer));
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, []);

  const status = {
    loading: 'Checking the API connection…',
    connected: 'Connected to the API',
    unavailable: 'API unavailable. Check that the service is running, then refresh this page.',
  }[connection];

  return (
    <main className="workspace">
      <header className="topbar">
        <span className="brand"><span className="brand-mark" aria-hidden="true">A</span> AI Security Agent</span>
      </header>
      <section className="intro" aria-labelledby="title">
        <h1 id="title">API connection</h1>
        <p className="description">This page checks whether the web interface can reach your local API.</p>
        <div className="status" role="status" data-state={connection}>
          <span className="status-dot" aria-hidden="true" />
          {status}
        </div>
      </section>
      <footer><a href="/api/health">View the API health response</a></footer>
    </main>
  );
}
