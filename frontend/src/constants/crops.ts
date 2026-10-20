// 7 Canonical Maharashtra Crops for FarmGenAI
export const CANONICAL_CROPS = [
  'Sugarcane',
  'Soybean',
  'Cotton',
  'Jowar',
  'Onion',
  'Bajra',
  'Rice'
] as const;

export type CanonicalCrop = typeof CANONICAL_CROPS[number];

// Statutory Benchmarks (MSP / Fair Remunerative Price 2026-27 in ₹/kg)
export const STATUTORY_BENCHMARKS: Record<string, number> = {
  'Sugarcane': 3.40,      // FRP ~₹340/quintal
  'Soybean': 48.92,       // MSP ₹4,892/quintal
  'Cotton': 71.21,        // Medium Staple MSP ₹7,121/quintal
  'Jowar': 33.71,         // Hybrid MSP ₹3,371/quintal
  'Onion': 25.00,         // Market benchmark floor ₹2,500/quintal
  'Bajra': 26.25,         // MSP ₹2,625/quintal
  'Rice': 23.00           // Common Paddy MSP ₹2,300/quintal
};

// 36 Maharashtra Districts with Center Coordinates for MandiMitra
export const MAHARASHTRA_DISTRICT_COORDINATES: Record<string, { lat: number; lon: number }> = {
  'Ahmednagar': { lat: 19.0952, lon: 74.7496 },
  'Akola': { lat: 20.7002, lon: 77.0082 },
  'Amravati': { lat: 20.9374, lon: 77.7796 },
  'Aurangabad': { lat: 19.8762, lon: 75.3433 },
  'Beed': { lat: 18.9891, lon: 75.7601 },
  'Bhandara': { lat: 21.1667, lon: 79.6500 },
  'Buldhana': { lat: 20.5292, lon: 76.1843 },
  'Chandrapur': { lat: 19.9615, lon: 79.2961 },
  'Dhule': { lat: 20.9042, lon: 74.7749 },
  'Gadchiroli': { lat: 20.1809, lon: 79.9961 },
  'Gondia': { lat: 21.4602, lon: 80.1961 },
  'Hingoli': { lat: 19.7198, lon: 77.1481 },
  'Jalgaon': { lat: 21.0077, lon: 75.5626 },
  'Jalna': { lat: 19.8410, lon: 75.8863 },
  'Kolhapur': { lat: 16.7050, lon: 74.2433 },
  'Latur': { lat: 18.4088, lon: 76.5604 },
  'Mumbai City': { lat: 18.9220, lon: 72.8347 },
  'Mumbai Suburban': { lat: 19.0760, lon: 72.8777 },
  'Nagpur': { lat: 21.1458, lon: 79.0882 },
  'Nanded': { lat: 19.1383, lon: 77.3210 },
  'Nandurbar': { lat: 21.3694, lon: 74.2403 },
  'Nashik': { lat: 19.9975, lon: 73.7898 },
  'Osmanabad': { lat: 18.1856, lon: 76.0419 },
  'Palghar': { lat: 19.6967, lon: 72.7699 },
  'Parbhani': { lat: 19.2686, lon: 76.7708 },
  'Pune': { lat: 18.5204, lon: 73.8567 },
  'Raigad': { lat: 18.5158, lon: 73.1822 },
  'Ratnagiri': { lat: 16.9902, lon: 73.3120 },
  'Sangli': { lat: 16.8524, lon: 74.5815 },
  'Satara': { lat: 17.6805, lon: 74.0183 },
  'Sindhudurg': { lat: 16.1178, lon: 73.6934 },
  'Solapur': { lat: 17.6599, lon: 75.9064 },
  'Thane': { lat: 19.2183, lon: 72.9781 },
  'Wardha': { lat: 20.7453, lon: 78.6022 },
  'Washim': { lat: 20.1110, lon: 77.1340 },
  'Yavatmal': { lat: 20.3888, lon: 78.1204 }
};
