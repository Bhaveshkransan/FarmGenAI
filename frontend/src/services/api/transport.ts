import { api } from './index';

export interface Vehicle {
  vehicle_id: string;
  transporter_id: string;
  vehicle_type: string;
  vehicle_name?: string;
  capacity_kg: number;
  fuel_type: string;
  fuel_efficiency_kmpl: number;
  current_location?: string;
  refrigerated: boolean;
  temperature_min_c?: number;
  temperature_max_c?: number;
  status: string;
  rating: number;
  contact_number?: string;
  owner_contact?: string;
  image_url?: string;
  recommendation_score?: number;
}

export const listVehicles = async (status: string = 'AVAILABLE'): Promise<{ data: Vehicle[] }> => {
  const response = await api.get(`/transport/vehicles?status=${status}`);
  return response.data;
};

export const getVehicle = async (id: string): Promise<{ data: Vehicle }> => {
  const response = await api.get(`/transport/vehicles/${id}`);
  return response.data;
};

export const createVehicle = async (vehicle: Partial<Vehicle>): Promise<{ data: Vehicle }> => {
  const response = await api.post(`/transport/vehicles`, vehicle);
  return response.data;
};

export const updateVehicle = async (id: string, vehicle: Partial<Vehicle>): Promise<{ data: Vehicle }> => {
  const response = await api.put(`/transport/vehicles/${id}`, vehicle);
  return response.data;
};

export const deleteVehicle = async (id: string): Promise<void> => {
  await api.delete(`/transport/vehicles/${id}`);
};

export const searchVehicles = async (filters: any): Promise<{ data: Vehicle[] }> => {
  const response = await api.post(`/transport/vehicles/search`, filters);
  return response.data;
};

export const recommendVehicles = async (request: any): Promise<{ data: Vehicle[] }> => {
  const response = await api.post(`/transport/vehicles/recommend`, request);
  return response.data;
};

export const submitNegotiationStep = async (payload: any): Promise<any> => {
  const response = await api.post(`/transport/negotiate`, payload);
  return response.data;
};
