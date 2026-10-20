import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarClock, RefreshCw, Receipt, Route, ShieldAlert, Truck } from 'lucide-react';
import { api } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';
import { readTransportNegotiationHistory, TransportNegotiationHistoryEntry } from '@/features/transport/transportNegotiationHistory';

export default function TransportTransactions() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<TransportNegotiationHistoryEntry[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [bookingError, setBookingError] = useState('');

  const loadTransactions = async () => {
    setLoading(true);
    setBookingError('');
    setHistory(readTransportNegotiationHistory(user));
    try {
      const response = await api.get('/transport/bookings');
      setBookings(response.data?.data || []);
    } catch {
      setBookingError('Saved transport bookings could not be loaded. Negotiation records saved in this browser are still shown.');
      setBookings([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [user]);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-xs font-bold uppercase text-emerald-700">Transport operations</p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900"><Receipt size={22} /> Transactions</h1>
          <p className="mt-1 text-sm text-slate-500">Transport negotiation decisions and bookings for your account.</p>
        </div>
        <button onClick={loadTransactions} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </header>

      {bookingError && <div className="flex items-start gap-2 border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"><ShieldAlert size={17} className="mt-0.5 shrink-0" />{bookingError}</div>}

      <section className="border-b border-slate-200 pb-6">
        <div className="mb-3 flex items-center gap-2">
          <Route size={18} className="text-emerald-700" />
          <h2 className="text-base font-bold text-slate-900">Negotiation decisions</h2>
          <span className="text-xs text-slate-500">{history.length} records</span>
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr><th className="px-4 py-3">Vehicle</th><th className="px-4 py-3">Load & route</th><th className="px-4 py-3">Freight</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Date</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? <tr><td colSpan={5} className="p-8 text-center text-slate-500">Loading transport records…</td></tr> : history.length === 0 ? <tr><td colSpan={5} className="p-8 text-center text-slate-500">No transport negotiation decisions recorded yet.</td></tr> : history.map(item => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3"><span className="font-semibold text-slate-900">{item.vehicleName}</span><span className="block text-xs text-slate-500">{item.vehicleType || 'Vehicle'}</span></td>
                  <td className="px-4 py-3"><span className="font-medium text-slate-800">{item.crop}, {item.quantityKg.toLocaleString()} kg</span><span className="block text-xs text-slate-500">{item.pickupLocation} → {item.deliveryLocation}</span></td>
                  <td className="px-4 py-3 font-semibold text-slate-800">{item.agreedPrice ? `₹${item.agreedPrice.toLocaleString('en-IN')}` : 'No agreement'}</td>
                  <td className="px-4 py-3"><span className="font-semibold text-slate-700">{item.status}</span><span className="block text-xs text-slate-500">Agent: {item.negotiationStatus}</span></td>
                  <td className="px-4 py-3 text-xs text-slate-500">{new Date(item.decisionAt || item.createdAt).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button onClick={() => navigate('/dashboard/transport', { state: { activeTab: 'my_fleet' } })} className="mt-3 text-sm font-semibold text-emerald-700 hover:text-emerald-900">Review negotiation details in My Fleet & Deals</button>
      </section>

      <section>
        <div className="mb-3 flex items-center gap-2">
          <Truck size={18} className="text-blue-700" />
          <h2 className="text-base font-bold text-slate-900">Transport bookings</h2>
          <span className="text-xs text-slate-500">{bookings.length} records</span>
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr><th className="px-4 py-3">Booking</th><th className="px-4 py-3">Cargo</th><th className="px-4 py-3">Route</th><th className="px-4 py-3">Vehicle</th><th className="px-4 py-3">Cost</th><th className="px-4 py-3">Status</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? <tr><td colSpan={6} className="p-8 text-center text-slate-500">Loading transport bookings…</td></tr> : bookings.length === 0 ? <tr><td colSpan={6} className="p-8 text-center text-slate-500"><CalendarClock size={24} className="mx-auto mb-2 text-slate-300" />No transport bookings found for your account.</td></tr> : bookings.map(booking => (
                <tr key={booking.booking_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs font-semibold text-slate-700">{booking.booking_id}</td>
                  <td className="px-4 py-3 text-slate-800">{booking.crop || 'Produce'}<span className="block text-xs text-slate-500">{Number(booking.quantity || 0).toLocaleString()} kg</span></td>
                  <td className="px-4 py-3 text-slate-700">{booking.origin_location} → {booking.destination_location}<span className="block text-xs text-slate-500">{booking.distance_km ?? '—'} km</span></td>
                  <td className="px-4 py-3 text-slate-700">{booking.truck || booking.vehicle_id || 'Assigned vehicle'}</td>
                  <td className="px-4 py-3 font-semibold text-slate-800">{booking.estimated_cost != null ? `₹${Number(booking.estimated_cost).toLocaleString('en-IN')}` : '—'}</td>
                  <td className="px-4 py-3 text-slate-700">{booking.status || 'SCHEDULED'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
