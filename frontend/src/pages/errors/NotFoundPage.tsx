import React from 'react';
import { Link } from 'react-router-dom';
import { SearchX, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
      <div className="text-center max-w-md">
        <div className="mx-auto w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mb-6">
          <SearchX className="text-slate-400 w-12 h-12" />
        </div>
        <h1 className="text-4xl font-black text-slate-800 mb-2">404</h1>
        <h2 className="text-xl font-bold text-slate-700 mb-4">Page Not Found</h2>
        <p className="text-slate-500 mb-8">
          The module or dashboard you are looking for does not exist or has been moved in the latest enterprise deployment.
        </p>
        <Link 
          to="/dashboard"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition"
        >
          <ArrowLeft size={18} /> Return to Dashboard
        </Link>
      </div>
    </div>
  );
}
