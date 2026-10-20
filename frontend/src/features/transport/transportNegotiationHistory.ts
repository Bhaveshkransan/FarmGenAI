export type TransportNegotiationHistoryEntry = {
  id: string;
  batchId: string;
  vehicleId: string;
  vehicleName: string;
  vehicleType?: string;
  crop: string;
  quantityKg: number;
  pickupLocation: string;
  deliveryLocation: string;
  floorPrice: number;
  agreedPrice: number | null;
  status: string;
  negotiationStatus: string;
  transcript: any[];
  winner: boolean;
  createdAt: string;
  decisionAt?: string;
};

const getStorageKey = (user: any) => {
  const userId = user?.user_id || user?.id || user?.email || 'anonymous';
  return `farmgenai:transport-negotiation-history:${userId}`;
};

export const readTransportNegotiationHistory = (user: any): TransportNegotiationHistoryEntry[] => {
  try {
    const stored = localStorage.getItem(getStorageKey(user));
    const entries = stored ? JSON.parse(stored) : [];
    return Array.isArray(entries) ? entries : [];
  } catch {
    return [];
  }
};

export const writeTransportNegotiationHistory = (
  user: any,
  entries: TransportNegotiationHistoryEntry[]
) => {
  localStorage.setItem(getStorageKey(user), JSON.stringify(entries));
};

export const updateTransportNegotiationHistory = (
  user: any,
  entryId: string,
  updates: Partial<TransportNegotiationHistoryEntry>
) => {
  const entries = readTransportNegotiationHistory(user).map(entry =>
    entry.id === entryId ? { ...entry, ...updates } : entry
  );
  writeTransportNegotiationHistory(user, entries);
  return entries;
};
