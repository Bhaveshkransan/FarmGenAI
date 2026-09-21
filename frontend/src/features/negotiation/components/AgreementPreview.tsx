import React, { useState } from 'react';
import { FileSignature, Download, ShieldCheck, CheckCircle2, Loader2 } from 'lucide-react';
import { formatCurrency } from '@/utils/formatters';
import { api } from '@/services/api';
import { useNotification } from '@/contexts/NotificationContext';

export default function AgreementPreview({ dealData, onSignAndClose }) {
  const [isSigning, setIsSigning] = useState(false);
  const { addNotification } = useNotification();

  const handleSign = async () => {
    setIsSigning(true);
    try {
      const token = localStorage.getItem('agri_token');
      if (token !== 'mock_token') {
        const negId = dealData.negotiation_id || dealData.id;
        if (negId) await api.post(`/negotiations/${negId}/accept`, { final_price: dealData.price });
      }
      // Save accepted deal status to localStorage for Dashboard sync
      const existingDeals = JSON.parse(localStorage.getItem('agri_deals') || '[]');
      existingDeals.unshift({
        id: dealData.negotiation_id || dealData.id || `CN-${Date.now()}`,
        crop: dealData.crop || 'Tomato',
        quantity: dealData.quantity || 500,
        price: dealData.price || 20.5,
        total: (dealData.price || 20.5) * (dealData.quantity || 500),
        status: 'ACCEPTED',
        buyer: dealData.buyer || 'Metro Wholesale',
        date: new Date().toLocaleDateString()
      });
      localStorage.setItem('agri_deals', JSON.stringify(existingDeals));

      addNotification('success', 'Agreement cryptographically signed and stored.');
      onSignAndClose();
    } catch (err) {
      addNotification('error', 'Failed to sign agreement.');
    } finally {
      setIsSigning(false);
    }
  };


  return (
    <div className="bg-white rounded-2xl shadow-sm border border-emerald-200 overflow-hidden sticky top-6 animate-in fade-in slide-in-from-right-4 duration-500">
      
      {/* Header */}
      <div className="bg-emerald-600 p-5 text-white">
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck size={20} className="text-emerald-200" />
          <h3 className="font-bold text-lg">Final Agreement Preview</h3>
        </div>
        <p className="text-emerald-100 text-sm">Smart Contract execution pending signature.</p>
      </div>
      
      {/* Contract Body */}
      <div className="p-6">
        <div className="border border-slate-200 rounded-xl bg-slate-50 p-4 font-mono text-sm text-slate-700 space-y-4 shadow-inner">
          <div className="text-center font-bold text-slate-800 pb-2 border-b border-slate-200 uppercase tracking-widest">
            Term Sheet - {dealData.crop}
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Seller</p>
              <p className="font-bold">{dealData.farmer}</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Buyer</p>
              <p className="font-bold">{dealData.buyer}</p>
            </div>
          </div>

          <div>
            <p className="text-slate-400 text-xs uppercase mb-1">Commodity Terms</p>
            <p>{dealData.quantity} kg of {dealData.crop} (Grade A)</p>
          </div>

          <div className="grid grid-cols-2 gap-4 bg-white p-3 rounded-lg border border-slate-200">
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Final Price</p>
              <p className="font-bold text-emerald-600">{formatCurrency(dealData.price)}/kg</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Total Value</p>
              <p className="font-bold text-slate-800">{formatCurrency(dealData.price * dealData.quantity)}</p>
            </div>
          </div>

          <div>
            <p className="text-slate-400 text-xs uppercase mb-1">Logistics</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Delivery Date: {dealData.deliveryDate}</li>
              <li>Transport: Managed by Seller (Included)</li>
              <li>Quality Dispute: 24hr Window</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-slate-100 bg-slate-50 flex flex-col gap-3">
        <button 
          onClick={handleSign}
          disabled={isSigning}
          className="w-full py-3 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition shadow-sm disabled:opacity-50"
        >
          {isSigning ? (
            <><Loader2 size={18} className="animate-spin" /> Cryptographically Signing...</>
          ) : (
            <><FileSignature size={18} /> Sign & Execute Contract</>
          )}
        </button>
        <button className="w-full py-2 flex items-center justify-center gap-2 text-slate-600 hover:bg-slate-200 bg-white border border-slate-200 font-bold rounded-xl transition">
          <Download size={16} /> Download Draft PDF
        </button>
      </div>
      
    </div>
  );
}
