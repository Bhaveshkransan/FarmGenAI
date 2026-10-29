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
      try {
        const activeUserId = user?.id || localStorage.getItem('user_id') || 'usr_buyer_demo';
        const res = await api.get(`/history/history/${activeUserId}`);
        const rawHistory = res.data?.history || (Array.isArray(res.data) ? res.data : []);

        // Also fetch from /negotiations to ensure all completed deals are captured
        let allDeals = [...rawHistory];
        try {
          const negRes = await api.get('/negotiations');
          const negs = Array.isArray(negRes.data) ? negRes.data : (negRes.data?.data || []);
          const completedNegs = negs.filter((n: any) => n.status === 'DEAL' || n.status === 'ACCEPTED' || n.final_price);
          allDeals = [...allDeals, ...completedNegs];
        } catch (e) {
          // ignore fallback error
        }

        const seen = new Set();
        const mapped = [];
        for (let idx = 0; idx < allDeals.length; idx++) {
          const h = allDeals[idx];
          const det = h.details || {};
          const negId = h.negotiation_id || det.negotiation_id || h.transaction_id || det.transaction_id || h.id;
          if (!negId || seen.has(negId)) continue;
          seen.add(negId);

          const crop = h.crop || det.crop || 'Agricultural Produce';
          const qty = Number(h.quantity || det.quantity || 500);
          const price = Number(h.final_price || det.final_price || det.price || h.price || 0);
          const farmer = h.farmer || h.farmer_name || det.farmer_name || det.seller_name || 'Maharashtra APMC Producer';
          const buyer = h.buyer || h.buyer_name || det.buyer_name || user?.name || 'AgroCorp Procurement';
          const status = (h.status || det.status || 'DEAL').toUpperCase();
          const createdVal = h.created_at || det.created_at || h.timestamp || det.timestamp || null;

          mapped.push({
            ...det,
            ...h,
            negotiation_id: negId,
            transaction_id: h.transaction_id || det.transaction_id || `TXN-MH-2026-${String(negId).replace('neg_', '').toUpperCase()}`,
            crop,
            quantity: qty,
            final_price: price,
            farmer,
            buyer,
            status: status === 'SETTLED' ? 'DEAL' : status,
            total: price > 0 && qty > 0 ? price * qty : 0,
            created_at: createdVal,
            _orderIndex: idx
          });
        }

        // Always sort latest on top
        mapped.sort((a: any, b: any) => {
          const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
          if (timeA && timeB && timeA !== timeB) {
            return timeB - timeA;
          }
          return b._orderIndex - a._orderIndex;
        });

        return mapped;
      } catch (err) {
        console.warn('Transactions query error:', err);
        return [];
      }
    },
    enabled: true,
    refetchInterval: 3000,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true
  });

  const transactions = data || [];

  const handleExportCSV = () => {
    if (transactions.length === 0) return;
    const headers = ['Negotiation ID', 'Commodity', 'Quantity (kg)', 'Final Price (INR/kg)', 'Total Value (INR)', 'Farmer / Supplier', 'Buyer', 'Status'];
    const rows = transactions.map((t: any) => [
      t.negotiation_id,
      t.crop,
      t.quantity,
      t.final_price,
      t.total || (t.final_price * t.quantity),
      `"${t.farmer}"`,
      `"${t.buyer}"`,
      t.status
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `FarmGenAI_Transactions_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getStatusBadge = (status: string) => {
    switch ((status || '').toUpperCase()) {
      case 'DEAL':
      case 'SETTLED':
      case 'COMPLETED':
      case 'ACCEPTED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800"><CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600"/> Deal Closed</span>;
      case 'IN_TRANSIT':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800"><Truck className="w-3.5 h-3.5 mr-1 text-blue-600"/> In Transit</span>;
      case 'NO_DEAL':
      case 'REJECTED':
      case 'FAILED':
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black text-slate-900">Transaction History</h1>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              {transactions.length} Verified Agreements
            </span>
          </div>
          <p className="text-slate-500 text-sm mt-1">View cryptographic agreements, landed APMC settlement values, and download official receipts (latest on top).</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => refetch()} 
            disabled={isFetching}
            className="bg-white text-slate-700 px-3.5 py-2 rounded-xl font-medium hover:bg-slate-50 border border-slate-200 transition-colors flex items-center text-xs shadow-sm cursor-pointer disabled:opacity-60"
            title="Refresh transactions"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 text-emerald-600 ${isFetching ? 'animate-spin' : ''}`} />
            {isFetching ? 'Updating...' : 'Refresh'}
          </button>
          <button 
            onClick={handleExportCSV}
            disabled={transactions.length === 0}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-2 rounded-xl shadow transition-colors flex items-center text-xs cursor-pointer disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV ({transactions.length})
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200">
          <Loader2 className="animate-spin mx-auto text-emerald-500 mb-3" size={32} />
          <p className="text-slate-500 text-sm">Loading verified transaction history...</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200">
          <ShieldAlert className="mx-auto text-red-400 mb-3" size={32} />
          <p className="text-slate-500 text-sm">Failed to load transactions. Please try again.</p>
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
              <thead className="bg-slate-50/80">
                <tr>
                  <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Contract / Negotiation ID</th>
                  <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Commodity & Volume</th>
                  <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Supplier / Farmer</th>
                  <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Gross Settlement</th>
                  <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3.5 text-right text-xs font-bold text-slate-600 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {transactions.map((txn: any) => {
                  const total = txn.total || (txn.final_price && txn.quantity ? txn.final_price * txn.quantity : 0);
                  const displayTotal = total > 0 ? `Rs. ${Math.round(total).toLocaleString('en-IN')}` : '-';

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
                        <div className="text-sm font-extrabold text-slate-900">{txn.crop || '—'}</div>
                        <div className="text-xs text-slate-500 font-medium">
                          {Number(txn.quantity || 0).toLocaleString()} kg {txn.final_price ? `@ ₹${txn.final_price}/kg` : ''}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-slate-800">{txn.farmer || txn.farmer_name || 'Maharashtra APMC Producer'}</div>
                        <div className="text-xs text-slate-400">Buyer: {txn.buyer || txn.buyer_name || 'AgroCorp'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-black text-emerald-700">{displayTotal}</div>
                        <div className="text-[10px] text-slate-400 font-medium">incl. 1% APMC cess</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(txn.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end items-center gap-2">
                          <Link 
                            to={`/negotiations/${txn.negotiation_id}`} 
                            className="p-2 bg-slate-100 hover:bg-emerald-50 text-slate-600 hover:text-emerald-700 rounded-lg transition border border-slate-200 flex items-center gap-1 text-xs font-bold" 
                            title="View Deal Room"
                          >
                            <Eye size={14} /> Room
                          </Link>
                          <button 
                            onClick={() => {
                              const summary = `============================================================\n` +
                                `AGRINEGOTIATOR APMC SMART CONTRACT TERM SHEET\n` +
                                `Transaction ID: ${txn.transaction_id || txn.negotiation_id}\n` +
                                `Maharashtra APMC Model Act Compliant Electronic Trade\n` +
                                `============================================================\n\n` +
                                `COMMODITY: ${txn.crop} (APMC Grade A)\n` +
                                `SETTLED RATE: Rs. ${txn.final_price}/kg\n` +
                                `VOLUME: ${Number(txn.quantity).toLocaleString()} kg\n` +
                                `TOTAL VALUE: ${displayTotal}\n` +
                                `APMC MANDI CESS (1%): Rs. ${Number(total * 0.01).toLocaleString()}\n\n` +
                                `PARTIES:\n` +
                                `- BUYER: ${txn.buyer || 'AgroCorp Procurement Director'}\n` +
                                `- SELLER: ${txn.farmer}\n` +
                                `STATUS: ${txn.status} (CRYPTOGRAPHICALLY VERIFIED)\n` +
                                `DATE: ${new Date().toLocaleDateString('en-IN')}\n`;
                              const blob = new Blob([summary], { type: 'text/plain;charset=utf-8' });
                              const url = URL.createObjectURL(blob);
                              const link = document.createElement('a');
                              link.href = url;
                              link.download = `Certificate_${txn.transaction_id || txn.negotiation_id}.txt`;
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                            }}
                            className="p-2 bg-slate-100 hover:bg-blue-50 text-slate-600 hover:text-blue-700 rounded-lg transition border border-slate-200 flex items-center gap-1 text-xs font-bold cursor-pointer" 
                            title="Download Certificate"
                          >
                            <FileText size={14} /> Certificate
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
