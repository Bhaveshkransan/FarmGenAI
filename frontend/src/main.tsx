import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '@/app/App'
import './index.css'

interface MainErrorBoundaryProps {
  children?: React.ReactNode;
}

interface MainErrorBoundaryState {
  hasError: boolean;
  error: any;
  info: any;
}

class ErrorBoundary extends React.Component<MainErrorBoundaryProps, MainErrorBoundaryState> {
  constructor(props: MainErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, info: any) {
    this.setState({ info });
    console.error("ErrorBoundary caught an error", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', background: '#450a0a', color: '#fca5a5', minHeight: '100vh', fontFamily: 'monospace' }}>
          <h2>React Crash Detected:</h2>
          <pre style={{ whiteSpace: 'pre-wrap', marginBottom: '20px' }}>{this.state.error?.toString()}</pre>
          <h3>Component Stack:</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{this.state.info?.componentStack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
