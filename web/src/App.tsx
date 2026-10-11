import { useEffect, useState } from "react";
import { session } from "./api";
import { SignIn } from "./SignIn";
import { Dashboard } from "./Dashboard";

export function App() {
  const [signedIn, setSignedIn] = useState(() => session.get() !== null);

  useEffect(() => {
    // Fired by api.ts when the token expires or is rejected.
    const out = () => setSignedIn(false);
    window.addEventListener("due:signed-out", out);
    return () => window.removeEventListener("due:signed-out", out);
  }, []);

  if (!signedIn) return <SignIn onSignedIn={() => setSignedIn(true)} />;
  return (
    <Dashboard
      onSignOut={() => {
        session.clear();
        setSignedIn(false);
      }}
    />
  );
}
