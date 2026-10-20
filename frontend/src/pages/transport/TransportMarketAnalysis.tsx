import { useState } from 'react';
import { Activity, Fuel, MapPinned, RefreshCw, TrendingUp, Truck } from 'lucide-react';
import { api } from '@/services/api';

const CANONICAL_CROPS = ['Wheat', 'Rice', 'Soybean', 'Cotton', 'Sugarcane', 'Onion', 'Tomato', 'Produce'];
const VEHICLE_OPTIONS = ['Cargo Three-Wheeler', 'Mini Truck', 'LCV', 'Medium Truck', 'Refrigerated Truck', 'Heavy Truck', 'Tractor + Trailer'];
const FUEL_OPTIONS = ['Diesel', 'Petrol', 'CNG', 'Electric'];

export default function TransportMarketAnalysis() {
  const [crop, setCrop] = useState('Soybean');
  const [mandiLocation, setMandiLocation] = useState('Nagpur');
  const [origin, setOrigin] = useState('Nagpur');
  const [destination, setDestination] = useState('Mumbai');
  const [quantityKg, setQuantityKg] = useState('5000');
  const [vehicleType, setVehicleType] = useState('Medium Truck');
  const [fuelType, setFuelType] = useState('Diesel');
  const [fuelEfficiency, setFuelEfficiency] = useState('8');
  const [returnTrip, setReturnTrip] = useState(false);
  const [waitingHours, setWaitingHours] = useState('0');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [market, setMarket] = useState<any>(null);
  const [routeAnalysis, setRouteAnalysis] = useState<any>(null);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError('');
    try {
      const [marketRes, routeRes] = await Promise.all([
        api.get('/market/intelligence', { params: { crop, location: mandiLocation } }),
        api.get('/transport/route-estimate', {
          params: {
            origin,
            destination,
            quantity_kg: Number(quantityKg) || 1000,
            crop,
            vehicle_type: vehicleType,
            fuel_type: fuelType,
            fuel_efficiency_kmpl: Number(fuelEfficiency) || 8,
            return_trip: returnTrip,
            waiting_hours: Number(waitingHours) || 0,
          },
        }),
      ]);
      setMarket(marketRes.data?.data || null);
      setRouteAnalysis(routeRes.data || null);
    } catch {
      setError('Could not update market analysis. Check route details and retry.');
    } finally {
      setLoading(false);
    }
  };

  const priceData = market?.mandi_data;
  const fuel = market?.fuel;
  const routes = routeAnalysis?.routes || [];
  const updatedAt = market?.timestamp ? new Date(market.timestamp).toLocaleTimeString() : '';
  const routeSource = routes[0]?.cost_source || (routeAnalysis ? 'Calculated' : 'Not queried');
  const sourceLabel = priceData?.source_type === 'live_api' ? 'Live APMC Feed' : priceData?.source_type === 'dataset' ? 'Maharashtra APMC Historical Dataset' : 'Fallback Market Estimate';

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="border-b border-slate-200 pb-5">
        <p className="text-xs font-bold uppercase text-emerald-700">Freight & commodities</p>
        <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold text-slate-900"><TrendingUp size={24} /> Market & Route Analysis</h1>
        <p className="mt-1 text-sm text-slate-500">Benchmark mandi prices, fuel costs, and per-km route freight in one operational view.</p>
      </header>

      <form onSubmit={event => { event.preventDefault(); fetchAnalysis(); }} className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs font-semibold text-slate-700">Crop
          <select value={crop} onChange={event => setCrop(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal">
            {CANONICAL_CROPS.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-700">Mandi location
          <input value={mandiLocation} onChange={event => setMandiLocation(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal" placeholder="District or APMC market" />
        </label>
        <label className="text-xs font-semibold text-slate-700">Pickup
          <input value={origin} onChange={event => setOrigin(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal" placeholder="Origin city or district" />
        </label>
        <label className="text-xs font-semibold text-slate-700">Delivery
          <input value={destination} onChange={event => setDestination(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal" placeholder="Destination market" />
        </label>
        <label className="text-xs font-semibold text-slate-700">Load quantity (kg)
          <input type="number" min="100" step="100" value={quantityKg} onChange={event => setQuantityKg(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal" />
        </label>
        <label className="text-xs font-semibold text-slate-700">Vehicle type
          <select value={vehicleType} onChange={event => setVehicleType(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal">
            {VEHICLE_OPTIONS.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-700">Fuel type
          <select value={fuelType} onChange={event => setFuelType(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal">
            {FUEL_OPTIONS.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-700">Mileage (km/L)
          <input type="number" min="1" step="0.5" value={fuelEfficiency} onChange={event => setFuelEfficiency(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal" />
        </label>
        <label className="text-xs font-semibold text-slate-700">Waiting hours
          <input type="number" min="0" step="0.5" value={waitingHours} onChange={event => setWaitingHours(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 p-2 text-sm font-normal" />
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
                      <td className="px-4 py-3 font-semibold text-emerald-800">₹{Number(route.opening_quote_rate_per_km || 0).toFixed(5)}/km<span className="block text-xs font-normal text-slate-500">₹{Number(route.opening_quote || 0).toLocaleString('en-IN')} trip quote</span><details className="mt-1 text-xs font-normal"><summary className="cursor-pointer text-emerald-700">Cost breakdown</summary><div className="mt-1 space-y-0.5 text-slate-500">{Object.entries(route.cost_breakdown || {}).map(([key, value]) => <p key={key}>{key.replaceAll('_', ' ')}: ₹{Number(value || 0).toLocaleString('en-IN')}</p>)}</div></details></td>
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
