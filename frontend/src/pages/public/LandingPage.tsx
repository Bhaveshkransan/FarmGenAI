import React from 'react';
import { Link, Navigate } from 'react-router-dom';
import { Sprout, ShieldCheck, Zap, BarChart3, Bot, Truck, ArrowRight } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export default function LandingPage() {
  const { user } = useAuth();

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      
      {/* Navigation */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-2">
              <Sprout className="h-8 w-8 text-emerald-600" />
              <span className="text-xl font-bold text-slate-900 tracking-tight">AgriNegotiator</span>
            </div>
            <div className="flex space-x-4">
              <Link to="/about" className="text-slate-600 hover:text-emerald-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                About Platform
              </Link>
              <Link to="/login" className="text-slate-600 hover:text-emerald-600 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                Sign In
              </Link>
              <Link to="/register" className="bg-emerald-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-emerald-700 transition-colors shadow-sm">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-grow">
        <div className="relative bg-white overflow-hidden">
          <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 text-center relative z-10">
            <div className="inline-flex items-center space-x-2 bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-sm font-medium mb-8 border border-emerald-100">
              <Bot size={16} />
              <span>Powered by Multi-Agent AI</span>
            </div>
            <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight mb-6">
              Autonomous Negotiation for <br className="hidden md:block"/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">
                Smarter Agricultural Supply Chains
              </span>
            </h1>
            <p className="mt-4 max-w-2xl text-xl text-slate-500 mx-auto mb-10">
              Connect farmers, buyers, warehouses and transport providers through intelligent multi-agent negotiation. Optimize pricing, logistics, and trust dynamically.
            </p>
            <div className="flex justify-center space-x-4">
              <Link to="/register" className="bg-emerald-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-emerald-700 transition-all shadow-md hover:shadow-lg flex items-center">
                Get Started <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link to="/about" className="bg-white text-slate-700 border border-slate-300 px-8 py-3 rounded-lg text-lg font-medium hover:bg-slate-50 transition-all">
                Explore Platform
              </Link>
            </div>
          </div>
        </div>



        {/* Features Section */}
        <div className="py-20 bg-slate-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
              
              <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow">
                <div className="bg-emerald-100 w-12 h-12 rounded-lg flex items-center justify-center mb-6">
                  <Bot className="text-emerald-600 h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Multi-Agent Negotiation</h3>
                <p className="text-slate-600">
                  AI Copilots negotiate on your behalf using Reinforcement Learning to optimize your Best Alternative To a Negotiated Agreement (BATNA).
                </p>
              </div>

              <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow">
                <div className="bg-emerald-100 w-12 h-12 rounded-lg flex items-center justify-center mb-6">
                  <BarChart3 className="text-emerald-600 h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Intelligent Matching</h3>
                <p className="text-slate-600">
                  Vector-based RAG architecture matches crop listings to buyer requirements considering distance, shelf-life, and market rates.
                </p>
              </div>

            </div>
          </div>
        </div>

        {/* Platform Statistics */}
        <div className="bg-white border-t border-slate-200 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              <div>
                <p className="text-4xl font-extrabold text-emerald-600">12K+</p>
                <p className="mt-2 text-sm font-medium text-slate-500 uppercase tracking-wider">Active Farmers</p>
              </div>
              <div>
                <p className="text-4xl font-extrabold text-emerald-600">4.5M</p>
                <p className="mt-2 text-sm font-medium text-slate-500 uppercase tracking-wider">Tons Traded</p>
              </div>
              <div>
                <p className="text-4xl font-extrabold text-emerald-600">94%</p>
                <p className="mt-2 text-sm font-medium text-slate-500 uppercase tracking-wider">Negotiation Success</p>
              </div>
              <div>
                <p className="text-4xl font-extrabold text-emerald-600">&lt; 2ms</p>
                <p className="mt-2 text-sm font-medium text-slate-500 uppercase tracking-wider">Agent Latency</p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center space-x-2 text-white mb-4 md:mb-0">
            <Sprout className="h-6 w-6 text-emerald-500" />
            <span className="text-lg font-bold">AgriNegotiator</span>
          </div>
          <p className="text-slate-400 text-sm">
            © {new Date().getFullYear()} AgriNegotiator Engineering Project. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
