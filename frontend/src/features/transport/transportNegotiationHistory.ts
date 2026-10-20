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

export const DEFAULT_TRANSPORT_HISTORY: TransportNegotiationHistoryEntry[] = [
  {
    id: 'tneg_mh_01',
    batchId: 'BATCH-MH-2026-08',
    vehicleId: 'veh_dost_03',
    vehicleName: 'Ashok Leyland Dost+ (MH-15-EG-3341)',
    vehicleType: 'LCV',
    crop: 'Soybean',
    quantityKg: 1200,
    pickupLocation: 'Nashik APMC',
    deliveryLocation: 'Pune Market Yard',
    floorPrice: 3800,
    agreedPrice: 4200,
    status: 'CONFIRMED',
    negotiationStatus: 'ACCEPTED',
    transcript: [
      { role: 'buyer', text: 'Offered ₹3,800 for 1.2T lot delivery.', time: '10:15 AM' },
      { role: 'transporter_agent', text: 'Countered ₹4,200 factoring Nashik-Pune toll corridor.', time: '10:16 AM' },
      { role: 'buyer', text: 'Agreed at ₹4,200. Dispatch confirmed.', time: '10:18 AM' }
    ],
    winner: true,
    createdAt: new Date(Date.now() - 3600000 * 4).toISOString()
  },
  {
    id: 'tneg_mh_02',
    batchId: 'BATCH-MH-2026-09',
    vehicleId: 'veh_tata1109_04',
    vehicleName: 'Tata 1109 LPT (MH-20-DE-7788)',
    vehicleType: 'Medium Truck',
    crop: 'Onion',
    quantityKg: 5500,
    pickupLocation: 'Lasalgaon Mandi',
    deliveryLocation: 'Vashi APMC Mumbai',
    floorPrice: 7500,
    agreedPrice: 8200,
    status: 'IN_TRANSIT',
    negotiationStatus: 'ACCEPTED',
    transcript: [
      { role: 'buyer', text: 'Urgent 5.5T onion shipment to Mumbai required.', time: '08:30 AM' },
      { role: 'transporter_agent', text: 'Tata 1109 dispatched with digital e-way bill @ ₹8,200.', time: '08:32 AM' }
    ],
    winner: true,
    createdAt: new Date(Date.now() - 3600000 * 8).toISOString()
  },
  {
    id: 'tneg_mh_03',
    batchId: 'BATCH-MH-2026-10',
    vehicleId: 'veh_reefer_05',
    vehicleName: 'BharatBenz Reefer (MH-12-RF-9001)',
    vehicleType: 'Refrigerated Truck',
    crop: 'Grapes / Pomegranate',
    quantityKg: 4000,
    pickupLocation: 'Solapur APMC',
    deliveryLocation: 'JNPT Cold Port',
    floorPrice: 14000,
    agreedPrice: 15500,
    status: 'DELIVERED',
    negotiationStatus: 'COMPLETED',
    transcript: [
      { role: 'buyer', text: 'Need temperature controlled transit at 2-4 deg C.', time: 'Yesterday' },
      { role: 'transporter_agent', text: 'Reefer calibrated, agreed ₹15,500 total freight.', time: 'Yesterday' }
    ],
    winner: true,
    createdAt: new Date(Date.now() - 3600000 * 24).toISOString()
  }
];

export const readTransportNegotiationHistory = (user: any): TransportNegotiationHistoryEntry[] => {
  try {
    const stored = localStorage.getItem(getStorageKey(user));
    const entries = stored ? JSON.parse(stored) : [];
    if (Array.isArray(entries) && entries.length > 0) {
      return entries;
    }
    localStorage.setItem(getStorageKey(user), JSON.stringify(DEFAULT_TRANSPORT_HISTORY));
    return DEFAULT_TRANSPORT_HISTORY;
  } catch {
    return DEFAULT_TRANSPORT_HISTORY;
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
