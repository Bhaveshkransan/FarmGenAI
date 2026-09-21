import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ArrowLeft, Box, CheckCircle, Loader2 } from 'lucide-react';
import TrackingTimeline from '@/features/logistics/components/TrackingTimeline';
import DeliveryMap from '@/features/logistics/components/DeliveryMap';
import PaymentCard from '@/features/logistics/components/PaymentCard';
import { useNotification } from '@/contexts/NotificationContext';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export default function DealTracker() {
  const { id } = useParams();
  const token = localStorage.getItem('agri_token');
  const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/negotiation`;
  const { isConnected, lastMessage } = useWebSocket(wsUrl);
  const { addNotification } = useNotification();

  // Fetch real deal data from negotiation API
  const { data: negData, isLoading } = useQuery({
    queryKey: ['deal-tracker', id],
    queryFn: async () => {
      const res = await api.get(`/negotiations/${id}`);
      return res.data?.data || res.data;
    },
    enabled: !!id,
  });

  const dealData = {
    id: id || '',
    farmer: negData?.farmer || 'Farmer',
    buyer: (negData?.selected_buyer?.buyer_name) || 'Buyer',
    crop: negData?.crop || '—',
    quantity: negData?.quantity || 0,
    price: negData?.final_price || 0,
    amount: (negData?.final_price || 0) * (negData?.quantity || 0),
  };

  // State Machine logic matching the Redis Events
  const [executionState, setExecutionState] = useState('AGREEMENT');

  useEffect(() => {
    if (lastMessage && lastMessage.type) {
      // Listen for Logistics Redis Stream events
      const logisticsEvents = [
        'WAREHOUSE_RESERVED',
        'TRANSPORT_ASSIGNED',
        'PICKUP_COMPLETED',
        'DELIVERY_COMPLETED',
        'PAYMENT_RELEASED'
      ];
      
      if (logisticsEvents.includes(lastMessage.type)) {
        setExecutionState(lastMessage.type);
        addNotification('info', `Logistics Update: ${lastMessage.type.replace('_', ' ')}`);
      }
    }
  }, [lastMessage, addNotification]);

  // Dev Tool: Manually advance the state machine for testing
  const advanceState = () => {
    const states = ['AGREEMENT', 'WAREHOUSE_RESERVED', 'TRANSPORT_ASSIGNED', 'PICKUP_COMPLETED', 'DELIVERY_COMPLETED', 'PAYMENT_RELEASED'];
    const currentIndex = states.indexOf(executionState);
    if (currentIndex < states.length - 1) {
      setExecutionState(states[currentIndex + 1]);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center">
        <div>
          <Link to="/" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-blue-600 mb-2 transition">
            <ArrowLeft size={16} className="mr-1" /> Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Box className="text-blue-600" /> Logistics Command Center
          </h1>
          <p className="text-slate-500 mt-1">Live tracking for Deal #{dealData.id.substring(0,8)}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="px-4 py-2 bg-slate-50 border rounded-lg text-sm font-medium text-slate-600 flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
            {isConnected ? 'Telemetry Active' : 'Offline'}
          </div>
          
          {/* DEV ONLY: Simulate backend events */}
          <button onClick={advanceState} className="text-[10px] uppercase font-bold text-slate-400 hover:text-blue-600 transition tracking-wider">
            [Dev] Simulate Next Event
          </button>
        </div>
      </div>
      
      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Timeline Stepper */}
        <div className="lg:col-span-1">
          <TrackingTimeline currentStep={executionState} />
        </div>

        {/* Right Column: Maps & Escrow */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="h-[400px]">
            <DeliveryMap status={executionState} />
          </div>
          <div className="h-64">
             <PaymentCard 
               status={executionState}
               amount={dealData.amount}
               farmer={dealData.farmer}
               buyer={dealData.buyer}
             />
          </div>
        </div>
        
      </div>

      {/* Completion State Overlay Trigger */}
      {executionState === 'PAYMENT_RELEASED' && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-bottom-4">
          <div className="flex items-center gap-4">
             <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600">
               <CheckCircle size={24} />
             </div>
             <div>
               <h3 className="font-bold text-emerald-800 text-lg">Contract Execution Complete</h3>
               <p className="text-emerald-600 text-sm">The logistics workflow is finished and escrow is closed.</p>
             </div>
          </div>
          <button className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition shadow-sm">
            Submit Post-Deal Feedback (RL)
          </button>
        </div>
      )}

    </div>
  );
}
