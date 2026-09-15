/**
 * Maharashtra Agricultural Supply Chain & APMC Mandi Counterparties
 * Strictly grounded in the 7 statutory Maharashtra crops:
 * Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice.
 */

export interface Counterparty {
  name: string;
  loc: string;
  dist: number;
  match: number;
  status: string;
  initial: number;
  latest: number;
  availableQty: number;
  minBatch: number;
  special: string;
  sectorBadge?: string;
}

export const SECTOR_METADATA: Record<string, { label: string; badge: string; note: string }> = {
  restaurant: {
    label: 'Restaurant & Cloud Kitchen Chain',
    badge: '🍽️ Kitchen Grade',
    note: 'Daily kitchen grading, sorted mesh bags, rapid farmgate delivery'
  },
  food_processing: {
    label: 'Food Processing & Milling',
    badge: '🏭 Processing Lot',
    note: 'Optical sorted, de-stoned, low foreign matter (<1%), FSSAI compliant'
  },
  oil_extraction: {
    label: 'Oil Extraction & Solvent Refining',
    badge: '🛢️ Oilseed Grade',
    note: 'High oil recovery guarantee (>18.5%), moisture certified (<9%)'
  },
  ginning_spinning: {
    label: 'Cotton Ginning & Textile Spinning',
    badge: '🧵 Fibre Certified',
    note: '29mm+ staple length, micronaire 3.8-4.2, moisture <8% ginning ready'
  },
  wholesale_trader: {
    label: 'APMC Mandi Wholesale Distribution',
    badge: '🏢 APMC Mandi Lot',
    note: 'Standard 50kg gunny packing, e-NAM verified transit pass'
  },
  retail_supermarket: {
    label: 'Supermarket Retail Chain',
    badge: '🛒 Retail Ready',
    note: 'Grade A uniform sizing (50-60mm), barcoded lots, shelf life 14+ days'
  },
  institutional: {
    label: 'Institutional & Govt Supply',
    badge: '🏫 Institutional Supply',
    note: 'FSSAI certified, monthly scheduled buffer delivery mandate'
  },
};

export const MAHARASHTRA_CROP_SUPPLIERS: Record<string, Array<{ name: string; loc: string; dist: number; match: number; status: string; special: string }>> = {
  Onion: [
    { name: 'Lasalgaon Kanda Apex FPO', loc: 'Nashik, Maharashtra', dist: 105, match: 97, status: 'Active (Leading Match)', special: 'APMC Red Onion Direct' },
    { name: 'Pimpalgaon Baswant Onion Farmers Co-op', loc: 'Nashik, Maharashtra', dist: 120, match: 95, status: 'Counter-offered', special: 'Sorted Mesh Lots' },
    { name: 'Dindori Red Onion Consortium', loc: 'Nashik, Maharashtra', dist: 135, match: 93, status: 'Evaluating...', special: 'Cleaned Lot Standard' },
    { name: 'Junnar Agri Producer Company', loc: 'Pune, Maharashtra', dist: 65, match: 91, status: 'Reviewing', special: 'Rapid Dispatch' },
    { name: 'Ahmednagar Kanda & Agro Producers Union', loc: 'Ahmednagar, Maharashtra', dist: 160, match: 89, status: 'Active', special: 'Bulk Warehouse Lot' },
  ],
  Soybean: [
    { name: 'Latur Solvent & Oilseeds Farmers FPO', loc: 'Latur, Maharashtra', dist: 220, match: 96, status: 'Active (Leading Match)', special: '18.5% Oil Content' },
    { name: 'Nanded Krishi Vikas Agro Consortium', loc: 'Nanded, Maharashtra', dist: 280, match: 94, status: 'Counter-offered', special: 'Moisture < 10%' },
    { name: 'Barshi Soybean Producers Union', loc: 'Solapur, Maharashtra', dist: 180, match: 93, status: 'Evaluating...', special: 'Certified Commercial Lot' },
    { name: 'Hingoli Green Oilseeds Cluster', loc: 'Hingoli, Maharashtra', dist: 310, match: 90, status: 'Reviewing', special: 'Bulk Hopper Delivery' },
    { name: 'Amravati Krishi Sahakari Sanstha', loc: 'Amravati, Maharashtra', dist: 390, match: 88, status: 'Active', special: 'Solvent Grade Lot' },
  ],
  Cotton: [
    { name: 'Vidarbha White Gold Farmers Producer Co.', loc: 'Wardha, Maharashtra', dist: 310, match: 97, status: 'Active (Leading Match)', special: '29mm Staple Length' },
    { name: 'Akola Cotton Growers Association', loc: 'Akola, Maharashtra', dist: 280, match: 95, status: 'Counter-offered', special: 'Micronaire 4.0' },
    { name: 'Yavatmal Kapas Utpadak Sahakari Sangh', loc: 'Yavatmal, Maharashtra', dist: 340, match: 93, status: 'Evaluating...', special: 'Moisture < 8%' },
    { name: 'Jalgaon Cotton Ginning Farmer Pool', loc: 'Jalgaon, Maharashtra', dist: 240, match: 91, status: 'Reviewing', special: 'Direct Ginning Pass' },
    { name: 'Chhatrapati Sambhajinagar Agri Consortium', loc: 'Aurangabad, Maharashtra', dist: 195, match: 89, status: 'Active', special: 'Clean Lint Baleable' },
  ],
  Sugarcane: [
    { name: 'Kolhapur Panchganga Cane Growers Co-op', loc: 'Kolhapur, Maharashtra', dist: 210, match: 97, status: 'Active (Leading Match)', special: 'High Sucrose 12.5% Brix' },
    { name: 'Sangli Krishna Valley Sugar Belt FPO', loc: 'Sangli, Maharashtra', dist: 190, match: 95, status: 'Counter-offered', special: 'Fresh Harvest Lot' },
    { name: 'Baramati Cane Producers Society', loc: 'Pune, Maharashtra', dist: 75, match: 93, status: 'Evaluating...', special: 'Express Gate Transit' },
    { name: 'Satara Cane & Bio-Agro Producers Group', loc: 'Satara, Maharashtra', dist: 115, match: 90, status: 'Reviewing', special: 'FRP Direct Compliant' },
    { name: 'Ahmednagar Sugar Cane Cooperative', loc: 'Ahmednagar, Maharashtra', dist: 150, match: 88, status: 'Active', special: 'Bulk Crusher Ready' },
  ],
  Rice: [
    { name: 'Indrayani Fragrant Rice Producers FPO', loc: 'Maval, Pune, Maharashtra', dist: 45, match: 97, status: 'Active (Leading Match)', special: 'Indrayani Aromatic Grade' },
    { name: 'Gondia Paddy Farmers Cooperative', loc: 'Gondia, Maharashtra', dist: 480, match: 94, status: 'Counter-offered', special: 'Long Grain Paddy' },
    { name: 'Bhandara Kolam Rice Producer Group', loc: 'Bhandara, Maharashtra', dist: 450, match: 92, status: 'Evaluating...', special: 'Milling Ready <12% Moist' },
    { name: 'Raigad Wada Kolam Farmers Union', loc: 'Raigad, Maharashtra', dist: 110, match: 90, status: 'Reviewing', special: 'GI Tagged Wada Kolam' },
    { name: 'Kolhapur Basmati & Brown Rice Cluster', loc: 'Kolhapur, Maharashtra', dist: 225, match: 88, status: 'Active', special: 'Premium Head Rice' },
  ],
  Jowar: [
    { name: 'Solapur Maldandi Jowar Growers Society', loc: 'Solapur, Maharashtra', dist: 205, match: 97, status: 'Active (Leading Match)', special: 'Maldandi M-35-1 Pure' },
    { name: 'Dharashiv Millets & Sorghum Producer Co.', loc: 'Osmanabad, Maharashtra', dist: 240, match: 95, status: 'Counter-offered', special: 'Nutri-Cereal Certified' },
    { name: 'Ahmednagar Dryland Jowar Collective', loc: 'Ahmednagar, Maharashtra', dist: 140, match: 92, status: 'Evaluating...', special: 'Machine Cleaned White' },
    { name: 'Beed Marathwada Agri Farmers Union', loc: 'Beed, Maharashtra', dist: 220, match: 90, status: 'Reviewing', special: 'Sun-Dried Commercial' },
    { name: 'Sangli Nutri-Cereal FPO', loc: 'Sangli, Maharashtra', dist: 195, match: 88, status: 'Active', special: 'Flour Milling Lot' },
  ],
  Bajra: [
    { name: 'Dhule Pearl Millet Farmers Federation', loc: 'Dhule, Maharashtra', dist: 260, match: 96, status: 'Active (Leading Match)', special: 'ICTP-8203 Bold Grain' },
    { name: 'Nashik Nutri-Cereal Consortium', loc: 'Malegaon, Nashik, Maharashtra', dist: 160, match: 94, status: 'Counter-offered', special: 'Graded Uniform Kernel' },
    { name: 'Sangamner Bajra Utpadak Sangh', loc: 'Ahmednagar, Maharashtra', dist: 130, match: 92, status: 'Evaluating...', special: 'Cleaned Seed Grade' },
    { name: 'Jalgaon Bajra Producer Company', loc: 'Jalgaon, Maharashtra', dist: 230, match: 90, status: 'Reviewing', special: 'Low Moisture < 11%' },
    { name: 'Solapur Bajra & Millets Cooperative', loc: 'Solapur, Maharashtra', dist: 210, match: 88, status: 'Active', special: 'Direct Mandi Inflow' },
  ],
};

export const MAHARASHTRA_BUYER_COUNTERPARTIES: Array<{ name: string; loc: string; dist: number; match: number; status: string; special: string }> = [
  { name: 'MahaAgro State Trading Apex', loc: 'Nagpur, Maharashtra', dist: 250, match: 96, status: 'Active (Leading Bid)', special: 'Govt Procurement Node' },
  { name: 'Navi Mumbai Vashi Wholesale Terminal', loc: 'Mumbai, Maharashtra', dist: 170, match: 95, status: 'Counter-offered', special: 'Vashi APMC Commission' },
  { name: 'Pune APMC Agro Food Processing Ltd', loc: 'Pune, Maharashtra', dist: 110, match: 93, status: 'Evaluating...', special: 'Direct Factory Inflow' },
  { name: 'Latur Agro Commodity Export Hub', loc: 'Latur, Maharashtra', dist: 280, match: 91, status: 'Reviewing', special: 'Export Inspection Standard' },
  { name: 'Baramati Fresh Foods Supply Union', loc: 'Baramati, Maharashtra', dist: 85, match: 89, status: 'Active', special: 'Same-Day Settlement' },
];

export function normalizeCropName(crop: string): string {
  const c = (crop || '').toLowerCase().trim();
  if (c.includes('onion') || c.includes('kanda') || c.includes('pyaz')) return 'Onion';
  if (c.includes('soy') || c.includes('soya')) return 'Soybean';
  if (c.includes('cotton') || c.includes('kapas')) return 'Cotton';
  if (c.includes('cane') || c.includes('sugar')) return 'Sugarcane';
  if (c.includes('rice') || c.includes('paddy') || c.includes('chawal')) return 'Rice';
  if (c.includes('jowar') || c.includes('sorghum')) return 'Jowar';
  if (c.includes('bajra') || c.includes('millet') || c.includes('pearl')) return 'Bajra';
  return 'Onion';
}

export function getMatchingCounterparties(
  crop: string,
  isBuyer: boolean,
  basePrice: number,
  quantity: number,
  sectorKey: string = 'food_processing'
): Counterparty[] {
  const normCrop = normalizeCropName(crop);
  const baseP = Math.max(1, Number(basePrice) || 45.0);
  const qty = Math.max(10, Number(quantity) || 500);
  const sector = SECTOR_METADATA[sectorKey] || SECTOR_METADATA['food_processing'];

  if (isBuyer) {
    const rawList = MAHARASHTRA_CROP_SUPPLIERS[normCrop] || MAHARASHTRA_CROP_SUPPLIERS['Onion'];
    return rawList.map((cp, idx) => {
      // Proportional lots: available lot slightly exceeds or matches user demand
      const avail = Math.round(qty * (1 + idx * 0.15));
      const minB = Math.min(qty, Math.max(10, Math.floor(qty * 0.4)));
      const initialP = Math.round((baseP * (1.08 + idx * 0.02)) * 10) / 10;
      const latestP = Math.round((baseP * (1.02 + idx * 0.015)) * 10) / 10;
      return {
        name: cp.name,
        loc: cp.loc,
        dist: cp.dist,
        match: Math.max(85, cp.match - idx * 2),
        status: cp.status,
        initial: initialP,
        latest: latestP,
        availableQty: avail,
        minBatch: minB,
        special: cp.special,
        sectorBadge: sector.badge,
      };
    });
  } else {
    return MAHARASHTRA_BUYER_COUNTERPARTIES.map((cp, idx) => {
      const avail = Math.round(qty * (1 + idx * 0.2));
      const minB = Math.min(qty, Math.max(10, Math.floor(qty * 0.4)));
      const initialP = Math.round((baseP * (0.92 - idx * 0.02)) * 10) / 10;
      const latestP = Math.round((baseP * (0.97 - idx * 0.015)) * 10) / 10;
      return {
        name: cp.name,
        loc: cp.loc,
        dist: cp.dist,
        match: Math.max(85, cp.match - idx * 2),
        status: cp.status,
        initial: initialP,
        latest: latestP,
        availableQty: avail,
        minBatch: minB,
        special: cp.special,
        sectorBadge: sector.badge,
      };
    });
  }
}
