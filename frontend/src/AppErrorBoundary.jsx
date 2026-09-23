import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default class AppErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { globalThis.console?.error?.("Dashboard render failure", error, info); }
  render() {
    if (!this.state.error) return this.props.children;
    return <main className="fatal-error" role="alert"><AlertTriangle /><h1>The account workspace could not be displayed</h1><p>Your data was not changed. Reload the application; if the problem continues, provide support with the time shown below.</p><time>{new Date().toLocaleString()}</time><button onClick={() => window.location.reload()}><RefreshCw />Reload workspace</button></main>;
  }
}
