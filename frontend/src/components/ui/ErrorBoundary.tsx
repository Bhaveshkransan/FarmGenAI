import React from 'react';
import { ShieldAlert, RefreshCcw, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    
    try {
      fetch('/log-error', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: error.message || String(error),
          stack: error.stack || '',
          componentStack: errorInfo?.componentStack || ''
        })
      }).catch(() => {});
    } catch (e) {}
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
          <div className="bg-white p-8 rounded-3xl shadow-xl max-w-lg w-full text-center border border-slate-100">
            <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
              <ShieldAlert className="text-red-600 w-8 h-8" />
            </div>
            <h1 className="text-2xl font-black text-slate-800 mb-2">Something went wrong.</h1>
            <p className="text-slate-500 mb-4">
              A critical rendering error occurred in this module.
            </p>
            <div className="text-left bg-slate-100 p-4 rounded-xl font-mono text-xs text-red-600 overflow-auto max-h-48 mb-8">
              <p className="font-bold">{this.state.error?.message || "Unknown error"}</p>
              <pre className="mt-2 text-[10px] leading-tight">{this.state.error?.stack}</pre>
            </div>
            
            {/* Safe fallback actions */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button 
                onClick={() => window.location.reload()}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition"
              >
                <RefreshCcw size={18} /> Reload Session
              </button>
              <a 
                href="/"
                className="flex items-center justify-center gap-2 px-6 py-3 bg-white text-slate-700 border border-slate-200 font-bold rounded-xl hover:bg-slate-50 transition"
              >
                <Home size={18} /> Return Home
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
