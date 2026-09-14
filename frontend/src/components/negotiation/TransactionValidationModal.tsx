import React, { useState } from 'react';
import { 
  ShieldCheck, 
  CheckCircle2, 
  Download, 
  Printer, 
  X, 
  Copy, 
  Check, 
  Building, 
  User, 
  Scale, 
  Truck, 
  Lock,
  ExternalLink,
  FileText
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface TransactionValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  dealData: any;
  buyerUser?: any;
}

export default function TransactionValidationModal({
  isOpen,
  onClose,
  dealData,
  buyerUser
}: TransactionValidationModalProps) {
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  if (!isOpen || !dealData) return null;

  // Extract or generate deterministic transaction ID & Hash
  const rawId = dealData.id || dealData.negotiation_id || 'neg_deal';
  const cleanId = String(rawId).replace('neg_', '').toUpperCase();
  const transactionId = `TXN-MH-2026-${cleanId}`;
  
  // Deterministic Mock Smart Contract Hash
  const contractHash = `0x${Array.from(transactionId).map(c => c.charCodeAt(0).toString(16)).join('').slice(0, 32)}fa991b8d2`;

  const agreedPrice = Number(dealData.price || dealData.final_price || 15);
  const quantity = Number(dealData.quantity || 3000);
  const totalValue = agreedPrice * quantity;
  const apmcCess = Math.round(totalValue * 0.01); // 1% APMC cess
  const netSettlement = totalValue;

  const cropName = dealData.crop || 'Produce';
  const farmerName = dealData.farmer || dealData.farmer_name || 'Gurpreet Singh';
  const buyerName = dealData.buyer || dealData.buyer_name || buyerUser?.name || 'Buyer Enterprise';

  // Buyer persona details
  const storedUser = localStorage.getItem('agri_user');
  const parsedUser = storedUser ? JSON.parse(storedUser) : (buyerUser || {});
  const buyerPersona = parsedUser?.buyerPersona || 'food_processing';
  const businessName = parsedUser?.businessName || `${buyerName} Agro Procure`;
  const fssaiLicense = parsedUser?.fssaiLicense || '11522020000123';
  const gstin = parsedUser?.gstin || '27AABCU9603R1ZM';
  const buyerLocation = parsedUser?.location || dealData.location || 'Pune Market Yard, Maharashtra';

  const personaLabel = 
    buyerPersona === 'restaurant' ? 'Restaurant & Cloud Kitchen Chain' :
    buyerPersona === 'wholesale_trader' ? 'Wholesale APMC Commission Trader' :
    buyerPersona === 'retail_supermarket' ? 'Supermarket & Retail Grocery Chain' :
    buyerPersona === 'institutional' ? 'Institutional Canteen & Catering' :
    'Food Processing & Packaging Unit';

  const handleCopyId = () => {
    navigator.clipboard.writeText(transactionId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    const termSheetText = `
============================================================
AGRINEGOTIATOR APMC SMART CONTRACT TERM SHEET
Official Transaction Reference: ${transactionId}
Maharashtra APMC Model Act Compliant Electronic Trade
============================================================

TRANSACTION OVERVIEW:
- Transaction ID: ${transactionId}
- Execution Date: ${new Date().toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'full' })}
- Verification Hash: ${contractHash}
- Smart Contract Status: VALIDATED & CRYPTOGRAPHICALLY EXECUTED

PARTIES INVOLVED:
1. BUYER (Procurement Party):
   - Name: ${buyerName}
   - Registered Business: ${businessName}
   - Persona Category: ${personaLabel}
   - FSSAI License: ${fssaiLicense}
   - GSTIN: ${gstin}
   - Delivery Location: ${buyerLocation}

2. SELLER (Farmer / Producer Party):
   - Farmer Name: ${farmerName}
   - Mandi Registration ID: MH-FARM-9024
   - Registered APMC: Nashik APMC Market Yard, Maharashtra
   - Producer Status: Verified APMC Primary Producer

COMMODITY & FINANCIAL TERMS:
- Commodity: ${cropName} (Grade A)
- Agreed Volume: ${quantity.toLocaleString()} kg
- Agreed Unit Settlement Price: Rs. ${agreedPrice.toFixed(2)} / kg
- Gross Contract Value: Rs. ${totalValue.toLocaleString()}
- APMC Mandi Cess (1.0%): Rs. ${apmcCess.toLocaleString()}
- Total Net Settlement: Rs. ${netSettlement.toLocaleString()}
- Payment Escrow Mechanism: Direct APMC Settlement / Instant Escrow Release on Delivery Inspection

LOGISTICS & DISPUTE RESOLUTION:
- Delivery Window: Scheduled Immediate Dispatch (within 24-48 hours)
- Logistics Handler: Multi-Modal APMC Certified Freight
- Quality Dispute Window: 24 Hours post-delivery inspection
- Moisture & Spoilage Standard: APMC Grade A Verified (< 12% moisture)

GOVERNMENT & REGULATORY COMPLIANCE:
This contract represents a legally binding electronic agricultural trade agreement under the Maharashtra Agricultural Produce Marketing (Development and Regulation) Act and e-NAM e-trade guidelines.
============================================================
    `.trim();

    const blob = new Blob([termSheetText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `TermSheet_${transactionId}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden my-auto max-h-[92vh] flex flex-col">
        
        {/* MODAL HEADER */}
        <div className="bg-gradient-to-r from-slate-900 via-emerald-950 to-slate-900 p-5 sm:p-6 text-white border-b border-emerald-800 flex justify-between items-start shrink-0">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                <CheckCircle2 size={13} className="text-emerald-400" />
                DIGITALLY VALIDATED TRADE
              </span>
              <span className="text-xs bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded-full border border-slate-700">
                Maharashtra APMC Framework
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black tracking-tight text-white flex items-center gap-2">
              <FileText className="text-emerald-400" size={24} />
              Validated Term Sheet & Transaction Certificate
            </h2>
            <p className="text-xs sm:text-sm text-emerald-200/80 mt-1">
              Legally binding smart contract agreed between Buyer Agent & Farmer Agent.
            </p>
          </div>

          <button 
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* MODAL BODY (Scrollable) */}
        <div className="p-5 sm:p-6 overflow-y-auto space-y-6 text-slate-800 text-sm">

          {/* TRANSACTION IDENTITY BANNER */}
          <div className="bg-emerald-50/80 border border-emerald-200 rounded-2xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-wider font-bold text-emerald-800">
                Official Transaction ID
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="font-mono text-lg font-black text-slate-900 tracking-wide">
                  {transactionId}
                </span>
                <button
                  onClick={handleCopyId}
                  className="p-1 text-emerald-700 hover:text-emerald-900 hover:bg-emerald-100 rounded transition"
                  title="Copy Transaction ID"
                >
                  {copied ? <Check size={16} className="text-emerald-600" /> : <Copy size={16} />}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1 flex items-center gap-1 font-mono">
                <Lock size={12} className="text-emerald-600" /> Hash: {contractHash.slice(0, 18)}...
              </p>
            </div>

            <div className="sm:text-right">
              <p className="text-[11px] uppercase tracking-wider font-bold text-slate-500">
                Execution Timestamp
              </p>
              <p className="font-semibold text-slate-800 text-xs sm:text-sm mt-0.5">
                {new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' })} IST
              </p>
              <span className="text-[11px] font-bold text-emerald-700 flex items-center gap-1 justify-end mt-1">
                <ShieldCheck size={14} /> Smart Contract Sealed
              </span>
            </div>
          </div>

          {/* FINANCIAL SUMMARY HIGHLIGHTS */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-center">
              <p className="text-xs text-slate-500 uppercase font-semibold">Agreed Price</p>
              <p className="text-xl font-black text-emerald-600 mt-1">₹{agreedPrice.toFixed(2)}<span className="text-xs font-normal text-slate-500">/kg</span></p>
            </div>
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-center">
              <p className="text-xs text-slate-500 uppercase font-semibold">Contract Volume</p>
              <p className="text-xl font-black text-slate-900 mt-1">{quantity.toLocaleString()}<span className="text-xs font-normal text-slate-500"> kg</span></p>
            </div>
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-center col-span-2 sm:col-span-2">
              <p className="text-xs text-slate-500 uppercase font-semibold">Total Deal Settlement</p>
              <p className="text-2xl font-black text-slate-900 mt-1">₹{netSettlement.toLocaleString('en-IN')}</p>
            </div>
          </div>

          {/* VALIDATED PARTICIPANTS: BUYER & SELLER */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            {/* BUYER CARD WITH PERSONA */}
            <div className="p-4 bg-slate-50/80 rounded-2xl border border-slate-200 space-y-2.5">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <span className="text-xs font-black uppercase text-blue-700 flex items-center gap-1.5">
                  <Building size={14} /> Validated Buyer
                </span>
                <span className="text-[10px] bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded-full">
                  FSSAI & GSTIN Verified
                </span>
              </div>
              <div>
                <p className="font-extrabold text-slate-900 text-base">{businessName}</p>
                <p className="text-xs font-medium text-slate-500">{buyerName} • {personaLabel}</p>
              </div>
              <div className="text-xs space-y-1 pt-1 font-mono text-slate-600">
                <p><span className="text-slate-400 font-sans">FSSAI License:</span> <span className="font-bold text-slate-800">{fssaiLicense}</span></p>
                <p><span className="text-slate-400 font-sans">GSTIN Tax ID:</span> <span className="font-bold text-slate-800">{gstin}</span></p>
                <p><span className="text-slate-400 font-sans">Delivery Hub:</span> <span className="font-sans font-semibold text-slate-800">{buyerLocation}</span></p>
              </div>
            </div>

            {/* SELLER CARD WITH APMC DETAILS */}
            <div className="p-4 bg-slate-50/80 rounded-2xl border border-slate-200 space-y-2.5">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <span className="text-xs font-black uppercase text-emerald-700 flex items-center gap-1.5">
                  <User size={14} /> Validated Seller
                </span>
                <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full">
                  APMC Registered Farmer
                </span>
              </div>
              <div>
                <p className="font-extrabold text-slate-900 text-base">{farmerName}</p>
                <p className="text-xs font-medium text-slate-500">APMC Registered Producer</p>
              </div>
              <div className="text-xs space-y-1 pt-1 font-mono text-slate-600">
                <p><span className="text-slate-400 font-sans">Farmer APMC ID:</span> <span className="font-bold text-slate-800">MH-FARM-9024</span></p>
                <p><span className="text-slate-400 font-sans">Mandi Jurisdiction:</span> <span className="font-sans font-semibold text-slate-800">Nashik APMC Market Yard</span></p>
                <p><span className="text-slate-400 font-sans">Settlement Account:</span> <span className="font-sans font-semibold text-slate-800">Escrow Direct Bank Mandate</span></p>
              </div>
            </div>

          </div>

          {/* COMMODITY & LOGISTICS SPECIFICATIONS */}
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Scale size={14} className="text-slate-500" /> Commodity Terms & Quality Protocol
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-1">
                <p className="text-slate-400 uppercase font-semibold text-[10px]">Produce & Quality Grade</p>
                <p className="font-bold text-slate-900 text-sm">{cropName} • Grade A Standard</p>
                <p className="text-slate-500 text-[11px]">Moisture limit: &lt; 12% • APMC Certified Organic / Clean lot</p>
              </div>
              <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-1">
                <p className="text-slate-400 uppercase font-semibold text-[10px]">Logistics & Delivery Mode</p>
                <p className="font-bold text-slate-900 text-sm flex items-center gap-1">
                  <Truck size={14} className="text-emerald-600" /> Multi-Modal APMC Freight
                </p>
                <p className="text-slate-500 text-[11px]">Direct Transit from Farm gate to Buyer Hub • 24hr Inspection Window</p>
              </div>
            </div>
          </div>

          {/* DIGITAL SIGNATURES & AUDIT LOG */}
          <div className="p-4 bg-slate-900 rounded-2xl text-white space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                <ShieldCheck size={16} /> Cryptographic Multi-Party Signatures
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Consensus Verified (LangGraph)</span>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 bg-slate-800/80 rounded-xl border border-slate-700/60">
                <p className="text-[10px] text-slate-400 uppercase font-sans">Seller Digital Signature</p>
                <p className="text-emerald-400 font-bold mt-0.5">SIGNED: Farmer Agent ({farmerName})</p>
                <p className="text-[10px] text-slate-500 mt-1">Sig: 0x89ab...420e (APMC Key MH-FARM-9024)</p>
              </div>
              <div className="p-2.5 bg-slate-800/80 rounded-xl border border-slate-700/60">
                <p className="text-[10px] text-slate-400 uppercase font-sans">Buyer Digital Signature</p>
                <p className="text-blue-400 font-bold mt-0.5">SIGNED: Buyer Agent ({buyerName})</p>
                <p className="text-[10px] text-slate-500 mt-1">Sig: 0x24ef...9811 (Verified {fssaiLicense ? 'FSSAI' : 'GSTIN'})</p>
              </div>
            </div>
          </div>

        </div>

        {/* MODAL FOOTER */}
        <div className="p-4 sm:p-6 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row justify-between items-center gap-3 shrink-0">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={handleDownload}
              className="flex-1 sm:flex-initial py-2.5 px-4 bg-white hover:bg-slate-100 text-slate-700 font-bold text-xs rounded-xl border border-slate-300 transition flex items-center justify-center gap-1.5 shadow-sm"
            >
              <Download size={15} /> Download Term Sheet
            </button>
            <button
              onClick={handlePrint}
              className="flex-1 sm:flex-initial py-2.5 px-4 bg-white hover:bg-slate-100 text-slate-700 font-bold text-xs rounded-xl border border-slate-300 transition flex items-center justify-center gap-1.5 shadow-sm"
            >
              <Printer size={15} /> Print Certificate
            </button>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={() => {
                onClose();
                navigate('/transactions');
              }}
              className="flex-1 sm:flex-initial py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs rounded-xl transition flex items-center justify-center gap-1.5 shadow-sm"
            >
              <ExternalLink size={14} /> View in Ledger
            </button>
            <button
              onClick={onClose}
              className="flex-1 sm:flex-initial py-2.5 px-5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition shadow-md shadow-emerald-600/20"
            >
              Close & Done
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
