export interface Artist {
  id: number;
  name_ru: string;
  name_en: string | null;
  is_group: boolean;
  bio: string | null;
}

export interface Technique {
  id: number;
  name: string;
  category: string | null;
}

export interface ImageData {
  id: number;
  url: string;
  is_primary: boolean;
  sort_order: number;
}

export interface Artwork {
  id: number;
  inventory_number: number;
  title: string | null;
  artist: Artist;
  year: number | null;
  edition: string | null;
  description: string | null;
  condition: string | null;
  has_expertise: boolean;
  status: string;
  location: string | null;
  width_cm: number | null;
  height_cm: number | null;
  purchase_price: number | null;
  sale_price: number | null;
  notes: string | null;
  techniques: Technique[];
  images: ImageData[];
  created_at: string;
  updated_at: string;
}

export interface ArtworkListItem {
  id: number;
  inventory_number: number;
  title: string | null;
  artist: Artist;
  status: string;
  sale_price: number | null;
  primary_image: string | null;
  year: number | null;
}

export interface Client {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  telegram: string | null;
  client_type: string;
  description: string | null;
  preferred_artists: Artist[];
  created_at: string;
}

export interface Sale {
  id: number;
  artwork_id: number;
  artwork_title: string | null;
  artist_name: string | null;
  client_id: number;
  client_name: string;
  referral_id: number | null;
  referral_name: string | null;
  sold_price: number;
  purchase_price: number | null;
  referral_fee: number | null;
  margin: number | null;
  notes: string | null;
  sold_at: string;
}

export interface DashboardSummary {
  total_sales: number;
  total_revenue: number;
  total_purchase: number;
  total_referral_fees: number;
  margin: number;
  artworks_by_status: Record<string, number>;
}

export const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  review: "На рассмотрении",
  for_sale: "В продаже",
  reserved: "Резерв",
  sold: "Продано",
  collection: "Коллекция",
};

export const CLIENT_TYPE_LABELS: Record<string, string> = {
  buyer: "Покупатель",
  dealer: "Дилер",
  referral: "Реферал",
};
