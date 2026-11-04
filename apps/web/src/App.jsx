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
    loading: 'בודק את החיבור לשרת…',
    connected: 'החיבור לשרת פעיל',
    unavailable: 'השרת אינו זמין כרגע. אפשר לרענן ולנסות שוב.',
  }[connection];

  return (
    <main className="workspace">
      <header className="topbar">
        <span className="brand" dir="ltr"><span className="brand-mark" aria-hidden="true">A</span> AI Security Agent</span>
        <span className="stage">שלב 1 מתוך 12</span>
      </header>
      <section className="intro" aria-labelledby="title">
        <p className="eyebrow">סביבת העבודה שלך</p>
        <h1 id="title">הבסיס לבדיקת<br />אבטחת האתר שלך.</h1>
        <p className="description">מרכז אחד לבדיקות HTTPS ותעודות TLS, ממצאים מוסברים והערכת התרעות שווא.</p>
        <div className="status" role="status" data-state={connection}>
          <span className="status-dot" aria-hidden="true" />
          {status}
        </div>
      </section>
      <section className="progress-card" aria-labelledby="progress-title">
        <div>
          <p className="eyebrow">התקדמות הפרויקט</p>
          <h2 id="progress-title">סביבת העבודה בהקמה</h2>
          <p>בשלב הזה נבנה הבסיס להפעלת המערכת. סריקת אתרים וניתוח ממצאים יתווספו בשלבים הבאים.</p>
        </div>
        <ol className="milestones">
          <li className="current"><span>01</span><div><strong>הקמת הסביבה</strong><small>השלב הנוכחי</small></div></li>
          <li><span>02</span><div><strong>הגדרת הבדיקות</strong><small>השלב הבא</small></div></li>
          <li><span>03</span><div><strong>ניהול סריקות</strong><small>בהמשך</small></div></li>
        </ol>
      </section>
      <footer>המערכת עדיין אינה מבצעת סריקות או מציגה הערכות אבטחה.</footer>
    </main>
  );
}
