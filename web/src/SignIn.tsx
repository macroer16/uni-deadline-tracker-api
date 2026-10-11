import { FormEvent, useState } from "react";
import { api } from "./api";

export function SignIn({ onSignedIn }: { onSignedIn: () => void }) {
  const [mode, setMode] = useState<"in" | "up">("in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "up") await api.register(email, password);
      await api.login(email, password);
      onSignedIn();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="signin">
      <h1 className="wordmark"><span className="mark">Due</span></h1>
      <p className="signin-lede">Every coursework deadline in one list, with the next one counting down at the top.</p>
      <form onSubmit={submit} className="signin-form">
        <label>
          Email
          <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={mode === "up" ? 10 : undefined}
            autoComplete={mode === "up" ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {mode === "up" && <span className="hint">At least 10 characters.</span>}
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{mode === "in" ? "Sign in" : "Create account"}</button>
      </form>
      <p className="switch">
        {mode === "in" ? "New here? " : "Already have an account? "}
        <button className="link" type="button" onClick={() => { setMode(mode === "in" ? "up" : "in"); setError(""); }}>
          {mode === "in" ? "Create an account" : "Sign in"}
        </button>
      </p>
    </main>
  );
}
