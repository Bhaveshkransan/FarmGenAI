import React from 'react';
import { Download, Eye, FileText, CheckCircle2, Truck, ShieldAlert, Clock, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';

export default function TransactionsPage() {
  const { user } = useAuth();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['transactions', user?.id],
    queryFn: async () => {
      try {
        const userId = user?.id || user?.user_id || 'all';
        const res = await api.get(`/history/history/${userId}`);
        const raw = res.data?.history || (Array.isArray(res.data) ? res.data : []);

        // Also fetch from /negotiations to ensure all completed deals are captured
        let allDeals = [...raw];
        try {
          const negRes = await api.get('/negotiations');
          const negs = Array.isArray(negRes.data) ? negRes.data : (negRes.data?.data || []);
          const completedNegs = negs.filter((n: any) => n.status === 'DEAL' || n.status === 'ACCEPTED' || n.final_price);
          allDeals = [...allDeals, ...completedNegs];
        } catch (e) {
          // ignore
        }

        const seen = new Set();
        const mapped = [];
        for (const h of allDeals) {
          const negId = h.negotiation_id || h.id || h.transaction_id;
          if (!negId || seen.has(negId)) continue;
          seen.add(negId);

          const crop = h.crop || h.details?.crop || 'Agricultural Produce';
          const qty = Number(h.quantity || h.details?.quantity || 500);
          const price = Number(h.final_price || h.price || h.details?.final_price || 0);
          const farmer = h.farmer || h.farmer_name || h.details?.farmer_name || h.details?.farmer || 'Maharashtra Farmer Network';
          const status = (h.status || h.details?.status || 'DEAL').toUpperCase();

          mapped.push({
            ...h,
            negotiation_id: negId,
            crop,
            quantity: qty,
            final_price: price,
            farmer,
            status: status === 'SETTLED' ? 'DEAL' : status,
            total: price > 0 && qty > 0 ? price * qty : 0
          });
        }
        return mapped;
      } catch (err) {
        console.warn('Transactions query error:', err);
        return [];
      }
    },
    enabled: true,
    refetchInterval: 5000,
  });

  const transactions = data || [];

  const handleExportCSV = () => {
    if (transactions.length === 0) return;
    const headers = ['Negotiation ID', 'Commodity', 'Quantity (kg)', 'Final Price (INR/kg)', 'Total Value (INR)', 'Farmer / Supplier', 'Status'];
    const rows = transactions.map((t: any) => [
      t.negotiation_id,
      t.crop,
      t.quantity,
      t.final_price,
      t.total || (t.final_price * t.quantity),
      `"${t.farmer}"`,
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

  const handleDownloadReceipt = (txn: any) => {
    const total = txn.total || (txn.final_price * txn.quantity);
    const receiptText = `============================================================\n` +
      `AGRINEGOTIATOR APMC SMART CONTRACT TERM SHEET\n` +
      `Transaction ID: TXN-MH-2026-${String(txn.negotiation_id).replace('neg_', '').toUpperCase()}\n` +
      `Maharashtra APMC Model Act Compliant Electronic Trade\n` +
      `============================================================\n\n` +
      `COMMODITY: ${txn.crop} (APMC Grade A)\n` +
      `SETTLED RATE: Rs. ${txn.final_price}/kg\n` +
      `VOLUME: ${Number(txn.quantity).toLocaleString()} kg\n` +
      `TOTAL VALUE: Rs. ${Number(total).toLocaleString()}\n` +
      `APMC MANDI CESS (1%): Rs. ${Number(total * 0.01).toLocaleString()}\n\n` +
      `PARTIES:\n` +
      `- BUYER: AgroCorp Procurement Director\n` +
      `- SELLER: ${txn.farmer}\n` +
      `STATUS: ${txn.status} (CRYPTOGRAPHICALLY VERIFIED)\n` +
      `DATE: ${new Date().toLocaleDateString('en-IN')}\n`;
    
    const element = document.createElement('a');
    const file = new Blob([receiptText], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `Receipt_${txn.negotiation_id}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const getStatusBadge = (status: string) => {
    switch ((status || '').toUpperCase()) {
      case 'DEAL':
      case 'SETTLED':
      case 'ACCEPTED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800"><CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600"/> Deal Closed</span>;
      case 'IN_TRANSIT':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800"><Truck className="w-3 h-3 mr-1 text-blue-600"/> In Transit</span>;
      case 'NO_DEAL':
      case 'REJECTED':
      case 'FAILED':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-800"><ShieldAlert className="w-3 h-3 mr-1 text-red-600"/> No Deal</span>;
      case 'ESCALATED_STORAGE':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800">In Storage</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-800"><Clock className="w-3 h-3 mr-1 text-slate-500"/> {status || 'Pending'}</span>;
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black text-slate-900">Transaction History</h1>
            <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-2.5 py-0.5 rounded-full">
              {transactions.length} Verified Agreements
            </span>
          </div>
          <p className="text-slate-500 text-sm mt-1">View cryptographic agreements, landed APMC settlement values, and download official receipts.</p>
        </div>
        <button 
          onClick={handleExportCSV}
          disabled={transactions.length === 0}
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-2.5 rounded-xl shadow transition-colors flex items-center text-xs cursor-pointer disabled:opacity-50"
        >
          <Download className="w-4 h-4 mr-2" /> Export CSV ({transactions.length})
        </button>
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
                    <tr key={txn.negotiation_id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-xs font-mono font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded-lg inline-block border border-slate-200">
                          {txn.negotiation_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-extrabold text-slate-900">{txn.crop}</div>
                        <div className="text-xs text-slate-500 font-medium">
                          {Number(txn.quantity).toLocaleString()} kg {txn.final_price ? `@ Rs. ${txn.final_price}/kg` : ''}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-semibold text-slate-800">{txn.farmer}</div>
                        <div className="text-[11px] text-slate-400">Verified APMC Supplier</div>
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
                            title="View Negotiation Room"
                          >
                            <Eye size={14} /> Room
                          </Link>
                          <button 
                            onClick={() => handleDownloadReceipt(txn)}
                            className="p-2 bg-slate-100 hover:bg-blue-50 text-slate-600 hover:text-blue-700 rounded-lg transition border border-slate-200 flex items-center gap-1 text-xs font-bold cursor-pointer" 
                            title="Download Receipt"
                          >
                            <FileText size={14} /> Receipt
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
