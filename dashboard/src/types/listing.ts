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
  scraped_at?: string | null;
}

