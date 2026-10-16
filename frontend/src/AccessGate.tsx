import { useEffect, useState, type ReactNode } from "react";
import { api, Button, setApiSession, type RecordData } from "./ui";

export function AccessGate({
  children,
}: {
  children: (account: RecordData, signOut: () => void) => ReactNode;
}) {
  const [account, setAccount] = useState<RecordData | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function refresh() {
    const session = await api("/auth/session");
    setApiSession(session.csrf);
    setAccount(session);
  }
  useEffect(() => {
    void refresh().catch((e) => setError(e.message));
    const expired = () => {
      setApiSession();
      setAccount({ mode: "accounts", authenticated: false });
      setError("Your session expired. Sign in again.");
    };
    window.addEventListener("continuum-session-expired", expired);
    return () =>
      window.removeEventListener("continuum-session-expired", expired);
  }, []);
  if (account?.mode === "demo" || account?.authenticated)
    return children(account, () => {
      setBusy(true);
      void api("/auth/logout", {})
        .then(() => {
          setApiSession();
          setAccount({ mode: "accounts", authenticated: false });
        })
        .catch((e) => setError(e.message))
        .finally(() => setBusy(false));
    });
  return (
    <main className="access-screen">
      <section className="panel access-card">
        <span className="section-label">CONTINUUM / COMPANY WORKSPACE</span>
        <h1>Sign in to your company context.</h1>
        <p>Your account determines the company and actions you can access.</p>
        {error && (
          <p role="alert" className="inline-error">
            {error}
          </p>
        )}
        {!account ? (
          <Button
            onClick={() => void refresh().catch((e) => setError(e.message))}
          >
            Retry connection
          </Button>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              void api("/auth/login", { username, password })
                .then(() => {
                  setPassword("");
                  return refresh();
                })
                .catch((e) => setError(e.message))
                .finally(() => setBusy(false));
            }}
          >
            <label>
              Username
              <input
                autoComplete="username"
                required
                maxLength={80}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                required
                maxLength={256}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <Button type="submit" loading={busy}>
              Sign in
            </Button>
          </form>
        )}
      </section>
    </main>
  );
}
