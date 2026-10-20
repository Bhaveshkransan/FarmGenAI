/**
 * Vehicle recommendation scoring logic for frontend display.
 * Note: Actual scoring is done on the backend. This can be used for client-side sorting if needed.
 */

export interface TransportRequest {
  quantity_kg: number;
  distance_km?: number;
  shelf_life_hours: number;
  urgency: 'NORMAL' | 'HIGH' | 'LOW';
  refrigerated_required: boolean;
  crop: string;
}

export interface VehicleStats {
  capacity_kg: number;
  refrigerated: boolean;
}

export const calculateVehicleScore = (
  vehicle: VehicleStats,
  request: TransportRequest,
  distance_km: number = 50
): number => {
  const W_DIST = 0.3;
  const W_SHELF = 0.2;
  const W_URGENCY = 0.2;
  const W_CAP = 0.15;
  const W_REFRIG = 0.15;

  const distanceScore = 100 / Math.max(distance_km, 1.0);

  const isPerishable = ['tomato', 'banana', 'strawberry', 'grape', 'mango', 'milk'].includes(
    request.crop.toLowerCase()
  );
  
  const shelfLifeFactor =
    request.shelf_life_hours > 48 && !isPerishable
      ? 1.0
      : 50.0 / Math.max(request.shelf_life_hours, 1.0);

  let urgencyFactor = 1.0;
  if (request.urgency === 'HIGH') urgencyFactor = 1.5;
  if (request.urgency === 'LOW') urgencyFactor = 0.5;

  const capacityRatio = request.quantity_kg > 0 ? vehicle.capacity_kg / request.quantity_kg : 1.0;
  const capacityFactor = capacityRatio < 1.0 ? 0.0 : Math.max(0.0, 2.0 - capacityRatio);

  const reqRefrig = request.refrigerated_required || isPerishable;
  const refrigFactor = reqRefrig && vehicle.refrigerated ? 1.0 : !reqRefrig ? 0.5 : 0.0;

  return (
    W_DIST * distanceScore +
    W_SHELF * shelfLifeFactor +
    W_URGENCY * urgencyFactor +
    W_CAP * capacityFactor +
    W_REFRIG * refrigFactor
  );
};
