import React, { useState } from 'react';
import { FileSignature, Download, ShieldCheck, CheckCircle2, Loader2, ExternalLink, FileText } from 'lucide-react';
import { formatCurrency } from '@/utils/formatters';
import { api } from '@/services/api';
import { useNotification } from '@/contexts/NotificationContext';
import TransactionValidationModal from '@/components/negotiation/TransactionValidationModal';

export default function AgreementPreview({ dealData, onSignAndClose }) {
  const [isSigning, setIsSigning] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const { addNotification } = useNotification();

  const rawId = dealData?.id || dealData?.negotiation_id || 'deal';
  const cleanId = String(rawId).replace('neg_', '').toUpperCase();
  const transactionId = `TXN-MH-2026-${cleanId}`;

  const handleSign = async () => {
    setIsSigning(true);
    try {
      const token = localStorage.getItem('agri_token');
      if (token !== 'mock_token') {
        const targetId = dealData.id || dealData.negotiation_id;
        await api.post(`/negotiations/${targetId}/accept`);
      }
      addNotification('success', 'Agreement cryptographically signed and stored.');
      setShowModal(true);
    } catch (err) {
      addNotification('error', 'Failed to sign agreement.');
    } finally {
      setIsSigning(false);
    }
  };

  return (
    <>
      <div className="bg-white rounded-2xl shadow-sm border border-emerald-200 overflow-hidden sticky top-6 animate-in fade-in slide-in-from-right-4 duration-500">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-700 to-emerald-600 p-4 text-white">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={18} className="text-emerald-200" />
              <h3 className="font-bold text-base">Final Agreement</h3>
            </div>
            <span className="text-[10px] bg-emerald-800/80 px-2 py-0.5 rounded font-mono font-bold text-emerald-200 border border-emerald-500/30">
              {transactionId}
            </span>
          </div>
          <p className="text-emerald-100 text-xs">Maharashtra APMC Validated Smart Contract</p>
        </div>
        
        {/* Contract Body */}
        <div className="p-4 space-y-3">
          <div className="border border-slate-200 rounded-xl bg-slate-50 p-3 font-mono text-xs text-slate-700 space-y-2.5 shadow-inner">
            <div className="flex justify-between items-center pb-2 border-b border-slate-200">
              <span className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                Term Sheet • {dealData.crop || 'Produce'}
              </span>
              <span className="text-[10px] text-emerald-700 font-bold bg-emerald-100 px-1.5 py-0.5 rounded">
                Grade A
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <p className="text-slate-400 uppercase text-[9px]">Seller</p>
                <p className="font-bold text-slate-800 truncate">{dealData.farmer || dealData.farmer_name || 'Farmer Agent'}</p>
              </div>
              <div>
                <p className="text-slate-400 uppercase text-[9px]">Buyer</p>
                <p className="font-bold text-slate-800 truncate">{dealData.buyer || dealData.buyer_name || 'Buyer Enterprise'}</p>
              </div>
            </div>

            <div className="bg-white p-2 rounded-lg border border-slate-200 flex justify-between items-center text-[11px]">
              <div>
                <p className="text-slate-400 text-[9px] uppercase">Final Price</p>
                <p className="font-bold text-emerald-600 text-sm">{formatCurrency(dealData.price)}/kg</p>
              </div>
              <div className="text-right">
                <p className="text-slate-400 text-[9px] uppercase">Total Value</p>
                <p className="font-bold text-slate-800 text-sm">{formatCurrency(dealData.price * (dealData.quantity || 500))}</p>
              </div>
            </div>

            <div className="text-[10px] text-slate-500 space-y-0.5 pt-1 border-t border-slate-200">
              <p>• Volume: {dealData.quantity || 500} kg • Delivery: {dealData.deliveryDate || 'Within 24-48h'}</p>
              <p>• Transport: Multi-Modal APMC Freight Included</p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-3 border-t border-slate-100 bg-slate-50 flex flex-col gap-2">
          <button 
            onClick={() => setShowModal(true)}
            className="w-full py-2.5 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition shadow-sm"
          >
            <FileText size={15} /> Open Validated Term Sheet
          </button>
          <button 
            onClick={handleSign}
            disabled={isSigning}
            className="w-full py-2 flex items-center justify-center gap-1.5 text-slate-700 hover:bg-slate-200 bg-white border border-slate-200 font-bold text-xs rounded-xl transition"
          >
            {isSigning ? (
              <><Loader2 size={14} className="animate-spin" /> Signing...</>
            ) : (
              <><FileSignature size={14} /> Execute & Validate</>
            )}
          </button>
        </div>
        
      </div>

      {/* Pop-up Transaction Validation Modal */}
      <TransactionValidationModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          if (onSignAndClose) onSignAndClose();
        }}
        dealData={dealData}
      />
    </>
  );
}
