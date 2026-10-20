import React, { useState, useEffect } from 'react';
import { X, Edit3, Save, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { api } from '@/services/api';

interface EditListingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  listing: any;
}

const QUALITY_GRADES = ['Premium (A+)', 'Grade A', 'Grade B', 'Grade C (Processing)'];
const LISTING_STATUSES = ['ACTIVE', 'NEGOTIATING', 'SOLD', 'EXPIRED'];

export default function EditListingModal({
  isOpen,
  onClose,
  onSuccess,
  listing
}: EditListingModalProps) {
  if (!isOpen || !listing) return null;

  const [quantity, setQuantity] = useState<number>(listing.quantity || 100);
  const [minSaleQty, setMinSaleQty] = useState<number>(listing.min_sale_quantity || 50);
  const [expectedPrice, setExpectedPrice] = useState<number>(listing.expected_price || 20);
  const [minPrice, setMinPrice] = useState<number>(listing.min_price || 18);
  const [grade, setGrade] = useState<string>(listing.grade || 'Grade A');
  const [shelfLife, setShelfLife] = useState<number>(listing.shelf_life || 7);
  const [location, setLocation] = useState<string>(listing.location || 'Nashik');
  const [status, setStatus] = useState<string>(listing.status || 'ACTIVE');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (listing) {
      setQuantity(listing.quantity || 100);
      setMinSaleQty(listing.min_sale_quantity || Math.min(50, listing.quantity || 100));
      setExpectedPrice(listing.expected_price || listing.price || 20);
      setMinPrice(listing.min_price || listing.price || 18);
      setGrade(listing.grade || 'Grade A');
      setShelfLife(listing.shelf_life || 7);
      setLocation(listing.location || 'Nashik');
      setStatus(listing.status || 'ACTIVE');
      setErrorMsg(null);
      setSuccessMsg(null);
    }
  }, [listing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    // Mathematical constraints
    if (minPrice > expectedPrice) {
      setErrorMsg('Minimum acceptable price cannot exceed expected price.');
      return;
    }
    if (minSaleQty > quantity) {
      setErrorMsg('Minimum sale quantity cannot be greater than total available quantity.');
      return;
    }
    if (quantity <= 0 || minPrice <= 0) {
      setErrorMsg('Quantity and prices must be strictly positive numbers.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        quantity: Number(quantity),
        min_sale_quantity: Number(minSaleQty),
        expected_price: Number(expectedPrice),
        min_price: Number(minPrice),
        grade,
        shelf_life: Number(shelfLife),
        location,
        status
      };

      await api.patch(`/listings/${listing.id}`, payload);
      setSuccessMsg('Listing updated successfully!');
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 700);
    } catch (err: any) {
      console.error('Failed to update listing:', err);
      setErrorMsg(err?.response?.data?.detail || 'Failed to update listing. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-gradient-to-r from-emerald-50/50 to-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-sm">
              <Edit3 size={18} />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-base">Edit Harvest Listing</h3>
              <p className="text-xs text-slate-500 font-mono">Lot #{listing.id?.substring(0, 10)} • {listing.crop}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4">
          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-600 flex items-center gap-2">
              <AlertCircle size={15} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-700 flex items-center gap-2 font-medium">
              <CheckCircle2 size={15} className="shrink-0 text-emerald-600" />
              <span>{successMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Total Quantity (kg)</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-400 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Min Sale Qty (kg)</label>
              <input
                type="number"
                value={minSaleQty}
                onChange={(e) => setMinSaleQty(parseFloat(e.target.value) || 0)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-400 outline-none"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Expected Price (₹/kg)</label>
              <input
                type="number"
                step="0.5"
                value={expectedPrice}
                onChange={(e) => setExpectedPrice(parseFloat(e.target.value) || 0)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-400 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Floor Price (₹/kg)</label>
              <input
                type="number"
                step="0.5"
                value={minPrice}
                onChange={(e) => setMinPrice(parseFloat(e.target.value) || 0)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-400 outline-none text-emerald-700 font-bold"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Quality Grade</label>
              <select
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 bg-white focus:ring-2 focus:ring-emerald-400 outline-none"
              >
                {QUALITY_GRADES.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Shelf Life (Days)</label>
              <input
                type="number"
                value={shelfLife}
                onChange={(e) => setShelfLife(parseInt(e.target.value) || 1)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-400 outline-none"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Origin Location</label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-400 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Listing Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full text-sm border border-slate-200 rounded-xl px-3.5 py-2.5 bg-white focus:ring-2 focus:ring-emerald-400 outline-none font-bold"
              >
                {LISTING_STATUSES.map((st) => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="pt-4 border-t border-slate-100 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-xl transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Saving Changes...
                </>
              ) : (
                <>
                  <Save size={14} /> Update Listing
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
