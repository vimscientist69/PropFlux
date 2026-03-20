export interface Listing {
  id?: number;
  job_id?: string | null;
  source_site?: string | null;
  title?: string | null;
  price?: string | null;
  location?: string | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  property_type?: string | null;
  listing_url?: string | null;
  suburb?: string | null;
  city?: string | null;
  province?: string | null;
  erf_size?: string | null;
  floor_size?: string | null;
  rates_and_taxes?: string | null;
  levies?: string | null;
  garages?: number | null;
  parking?: string | null;
  en_suite?: string | null;
  lounges?: string | null;
  backup_power?: string | null;
  security?: string | null;
  pets_allowed?: string | null;
  agent_name?: string | null;
  agent_phone?: string | null;
  agency_name?: string | null;
  listing_id?: string | null;
  date_posted?: string | null;
  scraped_at?: string | null;
}

