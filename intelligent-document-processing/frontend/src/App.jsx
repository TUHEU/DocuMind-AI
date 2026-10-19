import { useEffect, useState } from "react";
import { getHealth, getDbHealth } from "./api.js";

function Check({ label, state }) {
  const text =
    state === null ? "Checking..." : state.ok ? "OK" : state.error || "Failed";
  const cls = state === null ? "wait" : state.ok ? "ok" : "bad";
  return (
    <li className="check">
      <span>{label}</span>
      <strong className={cls}>{text}</strong>
    </li>
  );
}

export default function App() {
  const [api, setApi] = useState(null);
  const [db, setDb] = useState(null);

  async function run() {
    setApi(null);
    setDb(null);
    try {
      const r = await getHealth();
      setApi({ ok: r.ok, error: "HTTP " + r.status });
    } catch {
      setApi({ ok: false, error: "Backend not reachable" });
    }
    try {
      const r = await getDbHealth();
      setDb({ ok: r.ok, error: r.ok ? "" : "Database not connected" });
    } catch {
      setDb({ ok: false, error: "Backend not reachable" });
    }
  }

  useEffect(() => {
    run();
  }, []);

  return (
    <main className="page">
      <h1>DocuMind AI</h1>
      <p className="sub">Intelligent document processing. Development build.</p>
      <section className="card">
        <h2>System status</h2>
        <ul>
          <Check label="Backend API" state={api} />
          <Check label="MySQL database" state={db} />
        </ul>
        <button onClick={run}>Check again</button>
      </section>
    </main>
  );
}
