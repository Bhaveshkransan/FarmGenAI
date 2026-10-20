import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listVehicles, Vehicle } from '../../services/api/transport';
import { TruckIcon, StarIcon, MapPinIcon } from '@heroicons/react/24/outline';

const VehicleList: React.FC = () => {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchVehicles = async () => {
      try {
        const response = await listVehicles();
        setVehicles(response.data);
      } catch (error) {
        console.error('Error fetching vehicles:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchVehicles();
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-16 w-16 animate-spin rounded-full border-b-4 border-green-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8 pt-24 font-sans text-slate-800">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-900">
              Transport Fleet
            </h1>
            <p className="mt-2 text-lg text-slate-600">
              Find and book reliable transport for your produce.
            </p>
          </div>
          <button className="rounded-lg bg-green-600 px-6 py-3 font-semibold text-white shadow-lg transition-all hover:bg-green-700 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2">
            + List a Vehicle
          </button>
        </div>

        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {vehicles.map((vehicle) => (
            <div
              key={vehicle.vehicle_id}
              className="group relative flex cursor-pointer flex-col overflow-hidden rounded-2xl bg-white/70 shadow-lg backdrop-blur-md transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl"
              onClick={() => navigate(`/transporter/vehicles/${vehicle.vehicle_id}`)}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-green-50 to-white opacity-0 transition-opacity duration-300 group-hover:opacity-100"></div>
              
              <div className="relative h-48 w-full overflow-hidden bg-slate-200">
                {vehicle.image_url ? (
                  <img
                    src={vehicle.image_url}
                    alt={vehicle.vehicle_name}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-slate-100 text-slate-400">
                    <TruckIcon className="h-20 w-20" />
                  </div>
                )}
                {vehicle.refrigerated && (
                  <div className="absolute left-4 top-4 rounded-full bg-blue-100/90 px-3 py-1 text-xs font-semibold text-blue-800 shadow-sm backdrop-blur-sm">
                    Refrigerated
                  </div>
                )}
                <div className="absolute right-4 top-4 flex items-center rounded-full bg-white/90 px-2 py-1 text-xs font-bold text-slate-800 shadow-sm backdrop-blur-sm">
                  <StarIcon className="mr-1 h-3 w-3 text-yellow-500" />
                  {vehicle.rating.toFixed(1)}
                </div>
              </div>

              <div className="relative flex flex-1 flex-col p-5">
                <h3 className="text-xl font-bold text-slate-900">
                  {vehicle.vehicle_name || vehicle.vehicle_type}
                </h3>
                <div className="mt-1 flex items-center text-sm text-slate-500">
                  <MapPinIcon className="mr-1 h-4 w-4" />
                  {vehicle.current_location}
                </div>

                <div className="mt-4 flex flex-1 flex-col justify-end space-y-2 text-sm">
                  <div className="flex justify-between border-b border-slate-100 pb-2">
                    <span className="text-slate-500">Capacity</span>
                    <span className="font-semibold text-slate-800">{vehicle.capacity_kg} kg</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span className="text-slate-500">Fuel Type</span>
                    <span className="font-semibold text-slate-800">{vehicle.fuel_type}</span>
                  </div>
                </div>

                <button
                  className="mt-6 w-full rounded-lg bg-green-50 px-4 py-2 font-semibold text-green-700 transition-colors group-hover:bg-green-600 group-hover:text-white"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate('/dashboard/transport', { state: { prefillVehicle: vehicle } });
                  }}
                >
                  Request Transport
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default VehicleList;
