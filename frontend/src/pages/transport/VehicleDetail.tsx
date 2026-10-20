import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getVehicle, Vehicle } from '../../services/api/transport';
import { TruckIcon, StarIcon, MapPinIcon, ShieldCheckIcon, PhoneIcon } from '@heroicons/react/24/outline';

const VehicleDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchVehicle = async () => {
      try {
        if (id) {
          const response = await getVehicle(id);
          setVehicle(response.data);
        }
      } catch (error) {
        console.error('Error fetching vehicle details:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchVehicle();
  }, [id]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-16 w-16 animate-spin rounded-full border-b-4 border-green-600"></div>
      </div>
    );
  }

  if (!vehicle) {
    return (
      <div className="flex h-screen items-center justify-center text-xl text-slate-500">
        Vehicle not found.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8 pt-24 font-sans text-slate-800">
      <div className="mx-auto max-w-5xl">
        <button
          onClick={() => navigate('/transporter/vehicles')}
          className="mb-6 flex items-center text-sm font-semibold text-green-600 hover:text-green-700"
        >
          &larr; Back to Fleet
        </button>

        <div className="overflow-hidden rounded-3xl bg-white shadow-xl">
          <div className="relative h-80 w-full bg-slate-200 lg:h-96">
            {vehicle.image_url ? (
              <img
                src={vehicle.image_url}
                alt={vehicle.vehicle_name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-slate-100 text-slate-300">
                <TruckIcon className="h-32 w-32" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
            <div className="absolute bottom-8 left-8 right-8 flex items-end justify-between text-white">
              <div>
                <div className="flex items-center space-x-3">
                  <h1 className="text-4xl font-extrabold tracking-tight">
                    {vehicle.vehicle_name || vehicle.vehicle_type}
                  </h1>
                  {vehicle.refrigerated && (
                    <span className="rounded-full bg-blue-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-blue-200 backdrop-blur-md border border-blue-400/30">
                      Refrigerated
                    </span>
                  )}
                </div>
                <div className="mt-2 flex items-center text-lg text-slate-200">
                  <MapPinIcon className="mr-2 h-5 w-5" />
                  {vehicle.current_location}
                </div>
              </div>
              <div className="flex flex-col items-end">
                <div className="flex items-center rounded-xl bg-white/20 px-4 py-2 backdrop-blur-md">
                  <StarIcon className="mr-2 h-6 w-6 text-yellow-400" />
                  <span className="text-xl font-bold">{vehicle.rating.toFixed(1)}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-8 p-8 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <h2 className="text-2xl font-bold text-slate-900">Vehicle Specifications</h2>
              <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-3">
                <div className="rounded-2xl bg-slate-50 p-4 shadow-sm border border-slate-100">
                  <p className="text-sm font-medium text-slate-500">Capacity</p>
                  <p className="mt-1 text-xl font-bold text-slate-900">{vehicle.capacity_kg} <span className="text-sm font-normal text-slate-500">kg</span></p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4 shadow-sm border border-slate-100">
                  <p className="text-sm font-medium text-slate-500">Fuel Type</p>
                  <p className="mt-1 text-xl font-bold text-slate-900">{vehicle.fuel_type}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4 shadow-sm border border-slate-100">
                  <p className="text-sm font-medium text-slate-500">Efficiency</p>
                  <p className="mt-1 text-xl font-bold text-slate-900">{vehicle.fuel_efficiency_kmpl} <span className="text-sm font-normal text-slate-500">km/l</span></p>
                </div>
                {vehicle.refrigerated && (
                  <div className="col-span-2 rounded-2xl bg-blue-50 p-4 shadow-sm border border-blue-100 sm:col-span-3">
                    <p className="text-sm font-medium text-blue-600">Temperature Control</p>
                    <p className="mt-1 text-lg font-semibold text-blue-900">
                      {vehicle.temperature_min_c}°C to {vehicle.temperature_max_c}°C
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-10">
                <h2 className="text-2xl font-bold text-slate-900">About the Owner</h2>
                <div className="mt-6 flex items-start space-x-4 rounded-2xl bg-slate-50 p-6 border border-slate-100">
                  <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-green-100 text-green-600">
                    <ShieldCheckIcon className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-slate-900">Verified Transporter</p>
                    <p className="mt-1 text-slate-600">This vehicle is operated by a verified and highly-rated logistics partner on our platform. Your goods are fully insured during transit.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col space-y-6">
              <div className="rounded-3xl bg-green-50 p-6 shadow-inner border border-green-100">
                <h3 className="text-xl font-bold text-green-900">Book This Vehicle</h3>
                <p className="mt-2 text-sm text-green-700">Initiate a secure negotiation for your transport requirements.</p>
                
                <button
                  onClick={() => navigate('/dashboard/transport', { state: { prefillVehicle: vehicle } })}
                  className="mt-6 w-full rounded-xl bg-green-600 px-4 py-3 font-bold text-white shadow-lg transition-all hover:bg-green-700 hover:shadow-xl hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                >
                  Start Negotiation
                </button>
              </div>

              <div className="rounded-3xl bg-slate-50 p-6 border border-slate-100">
                <h3 className="font-semibold text-slate-900">Contact Info</h3>
                <div className="mt-4 flex items-center text-slate-600">
                  <PhoneIcon className="mr-3 h-5 w-5 text-slate-400" />
                  {vehicle.contact_number || vehicle.owner_contact || 'Available upon booking'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VehicleDetail;
