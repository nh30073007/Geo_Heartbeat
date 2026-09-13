// frontend/app/types/country.ts

export interface Country {
  id: string;
  name: string;
  code: string;
  region: string;
  capital: string;
  population: number;
  area: number;
  currency: string;
  flag: string;
}

export interface EconomyData {
  gdp: number;
  gdp_growth: number;
  inflation: number;
  unemployment: number;
  foreign_reserves: number;
  debt_to_gdp: number;
  export_growth: number;
  remittance: number;
  stability_score: number;
  recorded_at?: string;
}

export interface GovernmentData {
  party_name: string;
  leader_name: string;
  start_date: string;
  stability_score: number;
  state_legitimacy: number;
  human_rights_score: number;
  security_score: number;
  status: string;
  risk_factors: string[];
  strength_factors: string[];
  recorded_at?: string;
}

export interface CorruptionData {
  cpi_score: number;
  global_rank: number;
  perception_score: number;
  control_of_corruption: number;
  rule_of_law: number;
  government_effectiveness: number;
  regulatory_quality: number;
  bribery_score: number;
  nepotism_score: number;
  embezzlement_score: number;
  press_freedom_score: number;
  trend: string;
  recorded_at?: string;
}

export interface PredictionData {
  predicted_party: string;
  predicted_tenure_days: number;
  confidence_score: number;
  next_party_probabilities: Record<string, number>;
  best_case_tenure: number;
  worst_case_tenure: number;
  predicted_at?: string;
}

export interface SentimentData {
  overall_sentiment: number;
  party_support: Record<string, number>;
  sentiment_score: number;
  total_mentions: number;
  source_breakdown: Record<string, number>;
  top_hashtags: string[];
  emotion_distribution: Record<string, number>;
  recorded_at?: string;
}

export interface CountryDashboardData {
  country: Country;
  economy: EconomyData;
  government: GovernmentData;
  corruption: CorruptionData;
  prediction: PredictionData;
  sentiment: SentimentData;
}

export interface CountryResponse {
  success: boolean;
  data: CountryDashboardData;
  error?: string;
}

export interface CountryListItem {
  id: string;
  name: string;
  code: string;
  flag: string;
  region: string;
}

export interface CountryListResponse {
  success: boolean;
  data: {
    countries: CountryListItem[];
    total: number;
  };
}