import { AuthGuard } from "./components/auth/AuthGuard";
import { AppShell } from "./components/AppShell";

function App() {
  return (
    <AuthGuard>
      <AppShell />
    </AuthGuard>
  );
}

export default App;
