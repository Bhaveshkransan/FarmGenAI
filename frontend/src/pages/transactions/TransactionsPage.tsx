import React from 'react';
import { Download, Eye, FileText, CheckCircle2, Truck, ShieldAlert, Clock, Loader2, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';

export default function TransactionsPage() {
  const { user } = useAuth();

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['transactions', user?.id],
    queryFn: async () => {
      const activeUserId = user?.id || localStorage.getItem('user_id') || 'usr_buyer_demo';
      const res = await api.get(`/history/history/${activeUserId}`);
      const rawHistory = res.data?.history || [];
      const mapped = rawHistory
        .map((h: any, idx: number) => {
          const det = h.details || {};
          const createdVal = h.created_at || det.created_at || h.timestamp || det.timestamp || null;
          return {
            ...det,
            ...h,
            negotiation_id: h.negotiation_id || det.negotiation_id || h.transaction_id || det.transaction_id,
            transaction_id: h.transaction_id || det.transaction_id,
            crop: h.crop || det.crop || 'Produce',
            quantity: h.quantity || det.quantity,
            final_price: h.final_price || det.final_price || det.price,
            farmer: h.farmer || h.farmer_name || det.farmer_name || det.seller_name || 'Maharashtra APMC Producer',
            buyer: h.buyer || h.buyer_name || det.buyer_name || user?.name || 'Buyer Enterprise',
            status: (h.status || det.status || 'DEAL').toUpperCase(),
            created_at: createdVal,
            _orderIndex: idx
          };
        })
        .filter((h: any) => Boolean(h.negotiation_id || h.transaction_id));

      // Always sort latest on top
      mapped.sort((a: any, b: any) => {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        if (timeA && timeB && timeA !== timeB) {
          return timeB - timeA;
        }
        // Fallback: reverse insertion index so newly appended history appears at the top
        return b._orderIndex - a._orderIndex;
      });

      return mapped;
    },
    enabled: true,
    refetchInterval: 2500,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
  });

  const transactions = data || [];

  const getStatusBadge = (status: string) => {
    switch ((status || '').toUpperCase()) {
      case 'DEAL':
      case 'SETTLED':
      case 'COMPLETED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800"><CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600"/> Deal Closed</span>;
      case 'IN_TRANSIT':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800"><Truck className="w-3.5 h-3.5 mr-1 text-blue-600"/> In Transit</span>;
      case 'NO_DEAL':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800"><ShieldAlert className="w-3.5 h-3.5 mr-1 text-red-600"/> No Deal</span>;
      case 'ESCALATED_STORAGE':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800">In Storage</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-800"><Clock className="w-3.5 h-3.5 mr-1 text-slate-600"/> {status || 'Pending'}</span>;
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      
      {/* Header */}
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Transaction History</h1>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Sync
            </span>
          </div>
          <p className="text-slate-500 mt-1">View completed agreements and download invoices (latest on top).</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => refetch()} 
            disabled={isFetching}
            className="bg-white text-slate-700 px-3.5 py-2 rounded-lg font-medium hover:bg-slate-50 border border-slate-200 transition-colors flex items-center text-sm shadow-sm cursor-pointer disabled:opacity-60"
            title="Refresh transactions"
          >
            <RefreshCw className={`w-4 h-4 mr-2 text-emerald-600 ${isFetching ? 'animate-spin' : ''}`} />
            {isFetching ? 'Updating...' : 'Refresh'}
          </button>
          <button className="bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg font-medium hover:bg-emerald-100 border border-emerald-200 transition-colors flex items-center">
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200">
          <Loader2 className="animate-spin mx-auto text-emerald-500 mb-3" size={32} />
          <p className="text-slate-500">Loading your transaction history...</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200">
          <ShieldAlert className="mx-auto text-red-400 mb-3" size={32} />
          <p className="text-slate-500">Failed to load transactions. Please try again.</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && transactions.length === 0 && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200 border-dashed">
          <FileText className="mx-auto text-slate-300 mb-3" size={40} />
          <h3 className="font-bold text-slate-700 mb-1">No Transactions Yet</h3>
          <p className="text-slate-500 text-sm">Start a negotiation from your dashboard to create your first deal.</p>
        </div>
      )}

      {/* Table */}
      {!isLoading && transactions.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Negotiation ID</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Commodity</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Farmer</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Amount</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {transactions.map((txn) => {
                  const total = txn.final_price && txn.quantity
                    ? `₹${(txn.final_price * txn.quantity).toLocaleString('en-IN')}`
                    : '—';
                  return (
                    <tr key={txn.transaction_id || txn.negotiation_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-slate-900 font-mono">
                          {txn.transaction_id || (txn.negotiation_id ? `TXN-MH-2026-${String(txn.negotiation_id).replace('neg_', '').toUpperCase()}` : 'TXN-MH-2026-DEAL')}
                        </div>
                        {txn.negotiation_id && (
                          <div className="text-[11px] font-mono text-slate-400">
                            Ref: {txn.negotiation_id}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-slate-900">{txn.crop || '—'}</div>
                        <div className="text-sm text-slate-500">
                          {txn.quantity ? `${txn.quantity} kg` : '—'}
                          {txn.final_price ? ` @ ₹${txn.final_price}/kg` : ''}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-slate-800">{txn.farmer || txn.farmer_name || 'Maharashtra APMC Producer'}</div>
                        <div className="text-xs text-slate-400">Buyer: {txn.buyer || txn.buyer_name || 'AgroCorp'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-black text-emerald-600">{total}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(txn.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-3">
                          <Link 
                            to={user?.role === 'buyer' ? `/buyer/negotiations/${txn.negotiation_id}` : `/negotiations/${txn.negotiation_id}`} 
                            className="text-slate-400 hover:text-emerald-600 transition" 
                            title="View Deal Room"
                          >
                            <Eye className="w-5 h-5" />
                          </Link>
                          <button 
                            onClick={() => {
                              const summary = `AGRINEGOTIATOR APMC SMART CONTRACT\nTransaction: ${txn.transaction_id || txn.negotiation_id}\nCrop: ${txn.crop}\nQuantity: ${txn.quantity} kg\nPrice: Rs. ${txn.final_price}/kg\nTotal: ${total}\nFarmer: ${txn.farmer}\nBuyer: ${txn.buyer}\nStatus: COMPLETED`;
                              const blob = new Blob([summary], { type: 'text/plain;charset=utf-8' });
                              const url = URL.createObjectURL(blob);
                              const link = document.createElement('a');
                              link.href = url;
                              link.download = `Certificate_${txn.transaction_id || txn.negotiation_id}.txt`;
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                            }}
                            className="text-slate-400 hover:text-blue-600 transition" 
                            title="Download Certificate"
                          >
                            <FileText className="w-5 h-5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
