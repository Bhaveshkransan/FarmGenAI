export type NegotiationStatus = 
  | 'ACTIVE' 
  | 'ACCEPTED' 
  | 'REJECTED' 
  | 'EXPIRED' 
  | 'INTERVENED' 
  | 'DEAL' 
  | 'ESCALATED_PROCESSING' 
  | 'ESCALATED_STORAGE' 
  | 'ESCALATED_HOLD' 
  | 'FAILED';

export interface OfferData {
  id?: string;
  agent?: string;
  sender?: string;
  price: number;
  quantity?: number;
  quality?: string;
  deliveryDate?: string;
  transportIncluded?: boolean;
  warehouseIncluded?: boolean;
  validity?: string;
  message?: string;
  reasoning?: string[];
}

export type RecommendationDealType = 'DEAL' | 'PROCESSING' | 'STORAGE' | 'HOLD' | 'COMPOST';

export interface NegotiationRecommendation {
  action?: RecommendationDealType | string;
  message: string;
  target_price?: number;
  holding_days?: number;
  net_revenue?: number;
  storage_cost?: number;
  processing_rate?: number;
  facility?: string;
  confidence?: number;
}

export interface NegotiationReflection {
  mistake?: string;
  lesson?: string;
  policy_update?: string;
  analysis?: string;
  timestamp?: string;
}

export interface NegotiationState {
  id: string;
  farmer?: string;
  farmer_name?: string;
  buyer?: string;
  buyer_name?: string;
  crop: string;
  quantity: number;
  status: NegotiationStatus;
  min_price?: number;
  target_price?: number;
  market_price?: number;
  final_price?: number;
  price?: number;
  recommendation?: string | NegotiationRecommendation;
  reflection?: string | NegotiationReflection;
  history?: any[];
  offers?: any[];
  created_at?: string;
  updated_at?: string;
}

export const NEGOTIATION_STATUS = {
  ACTIVE: 'ACTIVE',
  ACCEPTED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  EXPIRED: 'EXPIRED',
  INTERVENED: 'INTERVENED',
  DEAL: 'DEAL',
  ESCALATED_PROCESSING: 'ESCALATED_PROCESSING',
  ESCALATED_STORAGE: 'ESCALATED_STORAGE',
  ESCALATED_HOLD: 'ESCALATED_HOLD',
  FAILED: 'FAILED',
};

