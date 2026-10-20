import { FormEvent, useState } from 'react';
import { Activity, Fuel, MapPinned, RefreshCw, TrendingUp, Truck } from 'lucide-react';
import { api } from '@/services/api';

const CROPS = ['Soybean', 'Cotton', 'Jowar', 'Onion', 'Bajra', 'Rice', 'Sugarcane'];
const VEHICLE_EFFICIENCY: Record<string, number> = {
  'Cargo Three-Wheeler': 20,
  'Mini Truck': 14,
  LCV: 10,
  'Medium Truck': 8,
  'Refrigerated Truck': 6,
  'Heavy Truck': 5,
  'Tractor + Trailer': 7,
};
const VEHICLE_TYPES = Object.keys(VEHICLE_EFFICIENCY);
const FUEL_TYPES = ['Diesel', 'Petrol', 'CNG'];

export default function TransportMarketAnalysis() {
  const [crop, setCrop] = useState('Soybean');
  const [mandiLocation, setMandiLocation] = useState('Nashik');
  const [origin, setOrigin] = useState('Ahmednagar');
  const [destination, setDestination] = useState('Pune');
  const [quantityKg, setQuantityKg] = useState(3000);
  const [vehicleType, setVehicleType] = useState('Medium Truck');
  const [fuelType, setFuelType] = useState('Diesel');
  const [fuelEfficiency, setFuelEfficiency] = useState(8);
  const [returnTrip, setReturnTrip] = useState(false);
  const [waitingHours, setWaitingHours] = useState(0);
  const [market, setMarket] = useState<any>(null);
  const [routeAnalysis, setRouteAnalysis] = useState<any>(null);
  const [fuel, setFuel] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState('');

  const runAnalysis = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoading(true);
    setError('');
    try {
      const [marketResult, routeResult, fuelResult] = await Promise.allSettled([
        api.get('/market-intelligence/price', { params: { crop, location: mandiLocation } }),
        api.get('/transport/route-estimate', {
          params: {
            origin,
            destination,
            quantity_kg: quantityKg,
            crop,
            vehicle_type: vehicleType,
            fuel_type: fuelType,
            fuel_efficiency_kmpl: fuelEfficiency,
            return_trip: returnTrip,
            waiting_hours: waitingHours,
          }
        }),
        api.get('/transport/fuel-estimate', {
          params: {
            fuel_type: fuelType,
            location: origin,
            efficiency_kmpl: fuelEfficiency,
            capacity_kg: quantityKg,
            vehicle_type: vehicleType,
          }
        })
      ]);

      if (marketResult.status === 'fulfilled') setMarket(marketResult.value.data?.data || null);
      else setMarket(null);
      if (routeResult.status === 'fulfilled') setRouteAnalysis(routeResult.value.data || null);
      else setRouteAnalysis(null);
      if (fuelResult.status === 'fulfilled') setFuel(fuelResult.value.data || null);
      else setFuel(null);

      const failures = [marketResult, routeResult, fuelResult].filter(result => result.status === 'rejected').length;
      if (failures === 3) setError('Market, route, and fuel services are unavailable. Check that the backend and external data services are reachable.');
      else if (failures > 0) setError('Some data sources did not respond. Results below show only successful live service responses.');
      setUpdatedAt(new Date().toLocaleString());
    } finally {
      setLoading(false);
    }
  };

  const priceData = market?.price_data;
  const routes = routeAnalysis?.routes || [];
  const sourceLabel = priceData?.source || 'Source unavailable';
  const routeSource = routes.length ? (routes[0]?.cost_source || 'Transport cost estimate') : 'Unavailable';

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="border-b border-slate-200 pb-5">
        <p className="text-xs font-bold uppercase text-emerald-700">Transport operations</p>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900"><Activity size={22} /> Market & Freight Analysis</h1>
        <p className="mt-1 text-sm text-slate-500">Compare mandi prices with route-level freight costs using current backend market, fuel, and routing services.</p>
      </header>

      <form onSubmit={runAnalysis} className="grid grid-cols-1 gap-4 border-b border-slate-200 pb-6 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-xs font-semibold text-slate-600">Crop
          <select value={crop} onChange={event => setCrop(event.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
            {CROPS.map(item => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-600">Mandi / district
          <input value={mandiLocation} onChange={event => setMandiLocation(event.target.value)} required className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" />
        </label>
        <label className="text-xs font-semibold text-slate-600">Freight origin
          <input value={origin} onChange={event => setOrigin(event.target.value)} required className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" />
        </label>
        <label className="text-xs font-semibold text-slate-600">Freight destination
          <input value={destination} onChange={event => setDestination(event.target.value)} required className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" />
        </label>
        <label className="text-xs font-semibold text-slate-600">Load size (kg)
          <input type="number" min="1" value={quantityKg} onChange={event => setQuantityKg(Number(event.target.value))} required className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" />
        </label>
        <label className="text-xs font-semibold text-slate-600">Vehicle type
          <select value={vehicleType} onChange={event => {
            setVehicleType(event.target.value);
            setFuelEfficiency(VEHICLE_EFFICIENCY[event.target.value]);
          }} className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
            {VEHICLE_TYPES.map(item => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-600">Fuel type
          <select value={fuelType} onChange={event => setFuelType(event.target.value)} className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900">
            {FUEL_TYPES.map(item => <option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-600">Fuel efficiency (km/L)
          <input type="number" min="1" max="100" step="0.1" value={fuelEfficiency} onChange={event => setFuelEfficiency(Number(event.target.value))} required className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" />
        </label>
        <label className="text-xs font-semibold text-slate-600">Waiting time (hours)
          <input type="number" min="0" max="48" step="0.5" value={waitingHours} onChange={event => setWaitingHours(Number(event.target.value))} className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" />
        </label>
        <label className="flex items-center gap-2 self-end rounded-md border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
          <input type="checkbox" checked={returnTrip} onChange={event => setReturnTrip(event.target.checked)} className="h-4 w-4 accent-emerald-700" />
          Include empty return trip
        </label>
        <div className="flex items-end">
          <button type="submit" disabled={loading} className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-emerald-700 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-800 disabled:opacity-50">
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} /> {loading ? 'Updating…' : 'Run analysis'}
          </button>
        </div>
      </form>

      {error && <div className="border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{error}</div>}

      {!market && !routeAnalysis && !loading ? (
        <div className="border border-dashed border-slate-300 py-14 text-center text-sm text-slate-500">Set your crop and route, then run the analysis to fetch current market and freight data.</div>
      ) : (
        <>
          <section className="grid grid-cols-1 border-y border-slate-200 md:grid-cols-2 xl:grid-cols-4">
            <div className="border-b border-slate-200 p-5 md:border-r xl:border-b-0">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500"><Activity size={14} /> Modal mandi price</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{priceData?.modal_price != null ? `₹${Number(priceData.modal_price).toFixed(2)}/kg` : 'Unavailable'}</p>
              <p className="mt-1 text-xs text-slate-500">{priceData?.mandi || mandiLocation} · {priceData?.arrival_date || 'Date not supplied'}</p>
            </div>
            <div className="border-b border-slate-200 p-5 xl:border-b-0 xl:border-r">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500"><MapPinned size={14} /> Price range</p>
              <p className="mt-2 text-xl font-bold text-slate-900">{priceData?.min_price != null && priceData?.max_price != null ? `₹${Number(priceData.min_price).toFixed(2)} – ₹${Number(priceData.max_price).toFixed(2)}` : 'Unavailable'}</p>
              <p className="mt-1 text-xs text-slate-500">Per kg · {priceData?.trend || 'Trend unavailable'}</p>
            </div>
            <div className="border-b border-slate-200 p-5 md:border-r md:border-b-0 xl:border-r">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500"><Fuel size={14} /> {fuelType} benchmark</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{fuel?.fuel_price != null ? `₹${Number(fuel.fuel_price).toFixed(2)}/L` : 'Unavailable'}</p>
              <p className="mt-1 text-xs text-slate-500">{fuel?.location || origin}{fuel?.is_estimate ? ' · estimated' : ''}</p>
            </div>
            <div className="p-5">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase text-slate-500"><Truck size={14} /> Route service</p>
              <p className="mt-2 text-lg font-bold text-slate-900">{routeAnalysis?.vehicle_assumed || 'Unavailable'}</p>
              <p className="mt-1 text-xs text-slate-500">{fuelEfficiency} km/L · {returnTrip ? 'Return included' : 'One way'} · {waitingHours}h wait</p>
              <p className="mt-1 text-xs text-slate-500">{routeSource}</p>
            </div>
          </section>

          <section className="border-b border-slate-200 pb-6">
            <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="flex items-center gap-2 text-base font-bold text-slate-900"><RouteIcon /> Route and freight cost comparison</h2>
                <p className="mt-1 text-xs text-slate-500">{origin} → {destination} · {Number(quantityKg).toLocaleString()} kg · {crop} · rate × total driven distance = trip quote</p>
              </div>
              {updatedAt && <p className="text-xs text-slate-400">Updated {updatedAt}</p>}
            </div>
            <div className="overflow-x-auto border border-slate-200 bg-white">
              <table className="w-full min-w-[1000px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Route</th><th className="px-4 py-3">Loaded / total km</th><th className="px-4 py-3">Fuel / toll</th><th className="px-4 py-3">Floor rate</th><th className="px-4 py-3">Target rate</th><th className="px-4 py-3">Opening quote</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {routes.length === 0 ? <tr><td colSpan={6} className="p-8 text-center text-slate-500">No route estimates were returned.</td></tr> : routes.map((route: any, index: number) => (
                    <tr key={route.route_id || index} className={route.is_recommended ? 'bg-emerald-50/60' : ''}>
                      <td className="px-4 py-3"><span className="font-semibold text-slate-900">{route.name || `Route ${index + 1}`}</span>{route.is_recommended && <span className="ml-2 text-[10px] font-bold uppercase text-emerald-700">Lowest cost</span>}<span className="block text-xs text-slate-500">{route.route_path || `${origin} → ${destination}`}</span></td>
                      <td className="px-4 py-3 text-slate-700">{route.distance_km} km loaded<span className="block text-xs text-slate-500">{route.operational_distance_km} km total driven · {route.duration_hours} hrs one way</span></td>
                      <td className="px-4 py-3 text-slate-700">₹{Number(route.estimated_fuel || 0).toLocaleString('en-IN')} fuel<span className="block text-xs text-slate-500">₹{Number(route.estimated_toll || 0).toLocaleString('en-IN')} toll</span></td>
                      <td className="px-4 py-3 font-semibold text-slate-900">₹{Number(route.floor_rate_per_km || 0).toFixed(5)}/km<span className="block text-xs font-normal text-slate-500">₹{Number(route.floor_price || 0).toLocaleString('en-IN')} trip floor</span></td>
                      <td className="px-4 py-3 font-semibold text-slate-900">₹{Number(route.target_rate_per_km || 0).toFixed(5)}/km<span className="block text-xs font-normal text-slate-500">₹{Number(route.target_price || 0).toLocaleString('en-IN')} trip target</span></td>
                      <td className="px-4 py-3 font-semibold text-emerald-800">₹{Number(route.opening_quote_rate_per_km || 0).toFixed(5)}/km<span className="block text-xs font-normal text-slate-500">₹{Number(route.opening_quote || 0).toLocaleString('en-IN')} trip quote</span><details className="mt-1 text-xs font-normal"><summary className="cursor-pointer text-emerald-700">Cost breakdown</summary><div className="mt-1 space-y-0.5 text-slate-500">{Object.entries(route.cost_breakdown || {}).map(([key, value]) => <p key={key}>{key.replace(/_/g, ' ')}: ₹{Number(value || 0).toLocaleString('en-IN')}</p>)}</div></details></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="flex flex-wrap items-start justify-between gap-3 text-xs text-slate-500">
            <div><p className="font-semibold text-slate-700">Market data source: {sourceLabel}</p><p className="mt-1">{priceData?.district || mandiLocation}, Maharashtra · {priceData?.arrival_date || 'Observation date unavailable'}</p></div>
            <div className="text-right"><p className="font-semibold text-slate-700">Cost source: {routeSource}</p><p className="mt-1">₹/km is calculated over total driven km; multiplying by that distance gives the trip quote.</p></div>
          </section>
        </>
      )}
    </div>
  );
}

function RouteIcon() {
  return <span className="inline-flex text-emerald-700"><TrendingUp size={17} /></span>;
}