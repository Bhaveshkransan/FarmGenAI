import React from 'react';
import { FileText, Calendar, Truck, Warehouse, Check, X, ArrowRightLeft } from 'lucide-react';
import { formatCurrency } from '@/utils/formatters';

export default function OfferCard({ 
  agent, 
  price, 
  quantity, 
  quality,
  deliveryDate,
  transportIncluded,
  warehouseIncluded,
  validity,
  isFarmer,
  isTransport = false,
  isBuyer = false,
  onAction 
}: {
  agent?: string;
  price: number;
  quantity: number;
  quality?: string;
  deliveryDate?: string;
  transportIncluded?: boolean;
  warehouseIncluded?: boolean;
  validity?: string;
  isFarmer?: boolean;
  isBuyer?: boolean;
  onAction?: (type: string, price: number) => void;
}) {
  return (
    <div className={`flex flex-col mb-6 ${isFarmer ? 'items-end' : 'items-start'}`}>
      <span className="text-xs font-semibold text-slate-500 mb-1 mx-2">{agent}</span>
      
      <div className={`w-full max-w-sm sm:max-w-md rounded-2xl shadow-sm border overflow-hidden ${
        isFarmer ? 'bg-white border-emerald-200' : 'bg-white border-blue-200'
      }`}>
        
        {/* Header - Price Highlight */}
        <div className={`p-4 flex justify-between items-center ${isFarmer ? 'bg-emerald-50' : 'bg-blue-50'}`}>
          <div>
            <p className={`text-xs font-bold uppercase tracking-wider ${isFarmer ? 'text-emerald-600' : 'text-blue-600'}`}>
              Formal Offer
            </p>
            <p className="text-2xl font-black text-slate-800">{formatCurrency(price)}{!isTransport && <span className="text-sm font-medium text-slate-500">/kg</span>}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-500 font-medium mb-0.5">{isTransport ? 'Freight Cost' : 'Total Value'}</p>
            <p className="text-lg font-bold text-slate-700">{formatCurrency(isTransport ? price : price * quantity)}</p>
          </div>
        </div>

        {/* Details Grid */}
        <div className="p-4 grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
          <div className="flex items-start gap-2">
            <FileText size={16} className="text-slate-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500">Volume & Grade</p>
              <p className="font-medium text-slate-700">{quantity} kg (Grade {quality})</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Calendar size={16} className="text-slate-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-xs text-slate-500">Delivery By</p>
              <p className="font-medium text-slate-700">{deliveryDate}</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Truck size={16} className={`shrink-0 mt-0.5 ${transportIncluded ? 'text-emerald-500' : 'text-slate-400'}`} />
            <div>
              <p className="text-xs text-slate-500">Logistics</p>
              <p className="font-medium text-slate-700">{transportIncluded ? 'Seller Arranged' : 'Buyer Pickup'}</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Warehouse size={16} className={`shrink-0 mt-0.5 ${warehouseIncluded ? 'text-emerald-500' : 'text-slate-400'}`} />
            <div>
              <p className="text-xs text-slate-500">Cold Storage</p>
              <p className="font-medium text-slate-700">{warehouseIncluded ? 'Included (7 Days)' : 'Not Included'}</p>
            </div>
          </div>
        </div>

        {/* Validity */}
        <div className="px-4 py-2 bg-slate-50 border-t border-b border-slate-100 flex justify-between items-center text-xs text-slate-500">
          <span>Valid for: {validity}</span>
          <span className="font-medium">100% Payment on Delivery</span>
        </div>

        {/* Action Buttons (Only show for Farmer manual review mode, never for Buyer autonomous procurement) */}
        {!isBuyer && !isFarmer && onAction && (
          <div className="p-3 grid grid-cols-3 gap-2 bg-slate-50">
            <button 
              onClick={() => onAction('reject', price)} 
              className="flex justify-center items-center gap-1.5 py-2 px-1 rounded-lg text-xs font-bold text-red-600 bg-red-100/50 hover:bg-red-100 transition"
            >
              <X size={14}/> Reject
            </button>
            <button 
              onClick={() => onAction('counter', price)} 
              className="flex justify-center items-center gap-1.5 py-2 px-1 rounded-lg text-xs font-bold text-amber-600 bg-amber-100/50 hover:bg-amber-100 transition"
            >
              <ArrowRightLeft size={14}/> Counter
            </button>
            <button 
              onClick={() => onAction('accept', price)} 
              className="flex justify-center items-center gap-1.5 py-2 px-1 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 shadow-sm transition"
            >
              <Check size={14}/> Accept Deal
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
