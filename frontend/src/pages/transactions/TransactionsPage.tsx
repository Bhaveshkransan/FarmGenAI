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
      if (!user?.id) return [];
      const res = await api.get(`/history/history/${user.id}`);
      return (res.data?.history || []).filter(
        (h) => h.negotiation_id && h.crop
      );
    },
    enabled: !!user?.id,
  });

  const transactions = data || [];

  const getStatusBadge = (status) => {
    switch ((status || '').toUpperCase()) {
      case 'DEAL':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800"><CheckCircle2 className="w-3 h-3 mr-1"/> Deal Closed</span>;
      case 'IN_TRANSIT':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"><Truck className="w-3 h-3 mr-1"/> In Transit</span>;
      case 'NO_DEAL':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800"><ShieldAlert className="w-3 h-3 mr-1"/> No Deal</span>;
      case 'ESCALATED_STORAGE':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">In Storage</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800"><Clock className="w-3 h-3 mr-1"/> {status || 'Pending'}</span>;
    }
  };

  return (
    <div className="space-y-6 animate-slide-up">
      
      {/* Header */}
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Transaction History</h1>
          <p className="text-slate-500 mt-1">View completed agreements and download invoices.</p>
        </div>
        <button className="bg-emerald-50 text-emerald-700 px-4 py-2 rounded-lg font-medium hover:bg-emerald-100 border border-emerald-200 transition-colors flex items-center">
          <Download className="w-4 h-4 mr-2" /> Export CSV
        </button>
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
                    <tr key={txn.negotiation_id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-slate-900 font-mono">{txn.negotiation_id?.substring(0, 16)}...</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-slate-900">{txn.crop || '—'}</div>
                        <div className="text-sm text-slate-500">
                          {txn.quantity ? `${txn.quantity} kg` : '—'}
                          {txn.final_price ? ` @ ₹${txn.final_price}/kg` : ''}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-slate-900">{txn.farmer || txn.farmer_name || 'Unknown Farmer'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-bold text-emerald-600">{total}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(txn.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-3">
                          <Link to={`/negotiations/${txn.negotiation_id}`} className="text-slate-400 hover:text-emerald-600" title="View Negotiation Room">
                            <Eye className="w-5 h-5" />
                          </Link>
                          <button className="text-slate-400 hover:text-blue-600" title="Download Receipt">
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
