import React, { useState } from 'react';
import { Users, Search, Edit2, Ban, RefreshCw, Download, Loader2, AlertCircle } from 'lucide-react';
import DataTable from '@/components/ui/DataTable';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export default function UserManagement() {
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const res = await api.get('/admin/users');
      return res.data?.data || [];
    },
  });

  const allUsers = data || [];
  const filteredUsers = allUsers.filter(u =>
    !searchTerm ||
    (u.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u.user_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u.role || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u.email || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { header: 'User ID', accessor: 'user_id', className: 'font-mono text-xs text-slate-500' },
    { header: 'Name / Organization', accessor: 'name', className: 'font-bold text-slate-800' },
    { header: 'Email', accessor: 'email', className: 'text-xs text-slate-500' },
    {
      header: 'Role',
      accessor: 'role',
      render: (row) => (
        <span className={`px-2 py-1 text-[10px] font-bold tracking-wider rounded uppercase ${
          row.role === 'admin' ? 'bg-purple-100 text-purple-700' :
          row.role === 'farmer' ? 'bg-emerald-100 text-emerald-700' :
          row.role === 'buyer' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-700'
        }`}>
          {row.role || '—'}
        </span>
      )
    },
    {
      header: 'Verification',
      accessor: 'verification_status',
      render: (row) => (
        <span className={`px-2 py-1 text-[10px] font-bold tracking-wider rounded uppercase ${
          row.verification_status === 'VERIFIED' ? 'bg-green-100 text-green-700' :
          row.verification_status === 'PENDING' ? 'bg-amber-100 text-amber-700' :
          'bg-red-100 text-red-700'
        }`}>
          {row.verification_status || 'PENDING'}
        </span>
      )
    },
    {
      header: 'Trust Score',
      accessor: 'trust_score',
      render: (row) => (
        <span className="font-bold text-sm text-slate-700">
          {row.trust_score != null ? `${Number(row.trust_score).toFixed(1)}★` : '—'}
        </span>
      )
    },
    { header: 'Location', accessor: 'location', className: 'text-sm text-slate-500' },
    {
      header: 'Actions',
      accessor: 'actions',
      render: (row) => (
        <div className="flex items-center gap-2">
          <button className="p-1.5 text-blue-600 hover:bg-blue-50 rounded" title="Edit User"><Edit2 size={16}/></button>
          <button className="p-1.5 text-amber-600 hover:bg-amber-50 rounded" title="Reset Password"><RefreshCw size={16}/></button>
          <button className="p-1.5 text-red-600 hover:bg-red-50 rounded" title="Suspend User"><Ban size={16}/></button>
        </div>
      )
    }
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
        <div className="relative w-full sm:w-96">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search users by name, ID, role, email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500 text-sm"
          />
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-3 py-2 text-sm font-bold text-slate-600 bg-slate-50 hover:bg-slate-100 border rounded-lg transition"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-slate-600 bg-slate-50 hover:bg-slate-100 border rounded-lg transition w-full sm:w-auto justify-center">
            <Download size={16} /> Export CSV
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition w-full sm:w-auto justify-center">
            <Users size={16} /> Add User
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-100">
          <Loader2 className="animate-spin mx-auto text-blue-500 mb-3" size={32} />
          <p className="text-slate-500">Loading users from database...</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-100">
          <AlertCircle className="mx-auto text-red-400 mb-3" size={32} />
          <p className="text-slate-500 mb-2">Failed to load users.</p>
          <p className="text-xs text-slate-400">Make sure you are logged in as an admin.</p>
        </div>
      )}

      {/* Summary Bar */}
      {!isLoading && !isError && (
        <div className="flex gap-4 text-sm text-slate-600">
          <span className="bg-white px-4 py-2 rounded-xl border border-slate-100 shadow-sm">
            <strong className="text-slate-800">{allUsers.length}</strong> total users
          </span>
          <span className="bg-white px-4 py-2 rounded-xl border border-slate-100 shadow-sm">
            <strong className="text-emerald-700">{allUsers.filter(u => u.role === 'farmer').length}</strong> farmers
          </span>
          <span className="bg-white px-4 py-2 rounded-xl border border-slate-100 shadow-sm">
            <strong className="text-blue-700">{allUsers.filter(u => u.role === 'buyer').length}</strong> buyers
          </span>
          <span className="bg-white px-4 py-2 rounded-xl border border-slate-100 shadow-sm">
            <strong className="text-green-700">{allUsers.filter(u => u.verification_status === 'VERIFIED').length}</strong> verified
          </span>
        </div>
      )}

      {/* Main Table */}
      {!isLoading && !isError && (
        <div className="h-[600px]">
          <DataTable
            title={`Platform User Directory (${filteredUsers.length} shown)`}
            columns={columns}
            data={filteredUsers}
          />
        </div>
      )}
    </div>
  );
}
