import { z } from 'zod';

/**
 * Reusable validation schemas and functions for Enterprise Forms.
 */
export const Validation = {
  password: (password) => {
    const minLength = 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasLower = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecial = /[^A-Za-z0-9]/.test(password);
    
    if (password.length < minLength) return "Password must be at least 8 characters.";
    if (!hasUpper) return "Password must contain an uppercase letter.";
    if (!hasLower) return "Password must contain a lowercase letter.";
    if (!hasNumber) return "Password must contain a number.";
    if (!hasSpecial) return "Password must contain a special character.";
    
    return null;
  },
  email: (email) => {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!regex.test(email)) return "Invalid email address format.";
    return null;
  },
  phone: (phone) => {
    const regex = /^[6-9]\d{9}$/;
    if (!regex.test(phone)) return "Must be a valid 10-digit Indian phone number.";
    return null;
  },
  price: (price, minimumSupportPrice = 0) => {
    if (price <= 0) return "Price must be greater than zero.";
    if (price < minimumSupportPrice) return `Price cannot be below MSP (₹${minimumSupportPrice}).`;
    return null;
  },
  quantity: (qty, minVolume = 100) => {
    if (qty < minVolume) return `Minimum trade volume is ${minVolume} kg.`;
    return null;
  }
};

// --- ZOD SCHEMAS ---

const phoneRegex = /^[6-9]\d{9}$/;
const passwordSchema = z.string().min(8, "Password must be at least 8 characters")
  .regex(/[A-Z]/, "Must contain at least one uppercase letter")
  .regex(/[a-z]/, "Must contain at least one lowercase letter")
  .regex(/[0-9]/, "Must contain at least one number")
  .regex(/[^A-Za-z0-9]/, "Must contain at least one special character");

export const registrationSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
  phone: z.string().regex(phoneRegex, "Must be a valid 10-digit Indian phone number"),
  password: passwordSchema,
  confirmPassword: z.string(),
  role: z.enum(['farmer', 'buyer', 'warehouse', 'transport']),
  terms: z.literal(true, { errorMap: () => ({ message: "You must accept the terms" }) })
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
});

export const MAHARASHTRA_LOCATIONS = [
  "maharashtra", "all maharashtra", "any", "nashik", "pune", "mumbai", "nagpur", "aurangabad",
  "chhatrapati sambhajinagar", "sambhajinagar", "solapur", "kolhapur", "ahmednagar", "satara",
  "sangli", "amravati", "thane", "kalyan", "jalgaon", "latur", "dhule", "nanded", "akola",
  "chandrapur", "parbhani", "buldhana", "yavatmal", "ratnagiri", "sindhudurg", "beed", "jalna",
  "raigad", "palghar", "osmanabad", "dharashiv", "wardha", "bhandara", "gondia", "gadchiroli",
  "hingoli", "washim", "navi mumbai", "panvel", "baramati", "shirur", "manchar", "dindori",
  "lasalgaon", "pimpalgaon", "yeola", "malegaon", "sangamner", "kopargaon", "shrirampur"
];

export const isMaharashtraLocation = (loc?: string): boolean => {
  if (!loc || !loc.trim()) return true; // Optional, defaults to Maharashtra
  const lower = loc.toLowerCase().trim();
  return MAHARASHTRA_LOCATIONS.some(dist => lower.includes(dist));
};

export const listingSchema = z.object({
  crop: z.string().min(2, "Crop name is required"),
  variety: z.string().min(1, "Variety is required"),
  grade: z.enum(['A', 'B', 'C']),
  quantity: z.number().min(10, "Minimum 10 kg required"),
  price: z.number().min(1, "Price must be greater than 0"),
  moisture: z.number().min(0).max(100, "Moisture must be between 0-100%").optional(),
  isOrganic: z.boolean().default(false),
  harvestDate: z.string().min(1, "Harvest date is required"),
  location: z.string().min(2, "Village/Taluka required").refine(isMaharashtraLocation, {
    message: "Location must be within Maharashtra (e.g. Nashik, Pune, Mumbai, Nagpur)"
  }),
  transportRequired: z.boolean().default(false),
  warehouseRequired: z.boolean().default(false),
  description: z.string().max(500).optional(),
});

export const TOP_MAHARASHTRA_CROPS = [
  "Sugarcane",
  "Soybean",
  "Cotton",
  "Jowar (Sorghum)",
  "Onion",
  "Bajra (Pearl Millet)",
  "Rice"
] as const;

export const CROP_ALIASES: Record<string, string[]> = {
  sugarcane: ['sugarcane', 'cane', 'ganna'],
  soybean: ['soybean', 'soya', 'soyabean'],
  cotton: ['cotton', 'kapas', 'raw cotton'],
  jowar: ['jowar', 'sorghum', 'great millet'],
  sorghum: ['jowar', 'sorghum', 'great millet'],
  onion: ['onion', 'onions', 'pyaz', 'kanda'],
  bajra: ['bajra', 'pearl millet', 'millet', 'sajje'],
  'pearl millet': ['bajra', 'pearl millet', 'millet'],
  rice: ['rice', 'paddy', 'chawal', 'dhan'],
  paddy: ['rice', 'paddy', 'chawal', 'dhan'],
  wheat: ['wheat', 'gehun'],
  tomato: ['tomato', 'tomatoes', 'tamatar'],
  potato: ['potato', 'potatoes', 'aloo']
};

/**
 * Intelligent crop matcher handling aliases and compound names (e.g. 'Jowar (Sorghum)' matches 'Jowar')
 */
export const matchCrops = (cropA?: string, cropB?: string): boolean => {
  if (!cropA || !cropB) return false;
  const a = cropA.toLowerCase().trim();
  const b = cropB.toLowerCase().trim();
  if (!a || !b) return false;
  if (a === b || a.includes(b) || b.includes(a)) return true;

  // Extract alphabetical words
  const wordsA = a.match(/[a-z]+/g) || [];
  const wordsB = b.match(/[a-z]+/g) || [];

  for (const wa of wordsA) {
    if (wordsB.includes(wa)) return true;
    const aliasesA = CROP_ALIASES[wa] || [];
    if (aliasesA.some(al => wordsB.includes(al) || b.includes(al))) return true;
  }
  for (const wb of wordsB) {
    const aliasesB = CROP_ALIASES[wb] || [];
    if (aliasesB.some(bl => wordsA.includes(bl) || a.includes(bl))) return true;
  }
  return false;
};

export const requirementSchema = z.object({
  crop: z.string()
    .min(2, "Crop name is required (at least 2 letters)")
    .regex(/^[A-Za-z\s()/-]+$/, "Crop name must only contain letters and standard characters (e.g. 'Jowar (Sorghum)')"),
  quality: z.enum(['A', 'B', 'C', 'ANY']),
  quantity: z.number({ invalid_type_error: "Volume must be a valid number" }).min(10, "Minimum volume is 10 kg").max(10000000, "Maximum volume is 10,000,000 kg"),
  maxBudget: z.number({ invalid_type_error: "Budget must be a valid number" }).min(1, "Price must be greater than ₹0/kg").max(10000, "Maximum price limit is ₹10,000/kg"),
  deliveryDate: z.string().min(1, "Delivery deadline is required").refine((val) => {
    if (!val) return false;
    const selected = new Date(val + 'T00:00:00');
    if (isNaN(selected.getTime())) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return selected >= today;
  }, { message: "Delivery deadline cannot be in the past" }).refine((val) => {
    const selected = new Date(val + 'T00:00:00');
    const maxFuture = new Date();
    maxFuture.setFullYear(maxFuture.getFullYear() + 2);
    return selected <= maxFuture;
  }, { message: "Delivery deadline cannot exceed 2 years into the future" }),
  preferredLocation: z.string().optional().refine((val) => {
    if (!val || !val.trim()) return true;
    return isMaharashtraLocation(val);
  }, { message: "Operational zone is strictly limited to Maharashtra (e.g. Nashik, Pune, Mumbai, Nagpur). Locations like other countries or states are not permitted." }),
  storageRequired: z.boolean().default(false),
  transportRequired: z.boolean().default(true),
});
