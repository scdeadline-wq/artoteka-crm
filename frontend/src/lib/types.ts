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
  is_internal: boolean;
  sort_order: number;
}

export interface Room {
  id: number;
  name: string;
  sort_order: number;
}

// Место хранения: kind = warehouse | rack | shelf (склад/адрес · стеллаж · полка)
export interface StorageOption {
  id: number;
  kind: string;
  name: string;
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
  provenance: string | null;
  style_period: string | null;
  has_expertise: boolean;
  status: string;
  warehouse: StorageOption | null;
  rack: StorageOption | null;
  shelf: StorageOption | null;
  width_cm: number | null;
  height_cm: number | null;
  purchase_price: number | null;
  sale_price: number | null;
  currency: string;
  notes: string | null;
  room: Room | null;
  is_framed: boolean;
  tags: string[];
  deleted_at: string | null;
  // Резерв: для кого держим, до какой даты (date-строка), заметка
  reserved_client_id: number | null;
  reserved_until: string | null;
  reserve_note: string | null;
  // Выставка с точными сроками (статус on_exhibition)
  exhibition_from: string | null;
  exhibition_to: string | null;
  exhibition_place: string | null;
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
  currency: string;
  primary_image: string | null;
  year: number | null;
  room: Room | null;
  is_framed: boolean;
  tags: string[];
  deleted_at: string | null;
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

export interface ClientPurchase {
  id: number;
  artwork_id: number;
  artwork_title: string | null;
  artist_name: string | null;
  sold_price: number;
  currency: string;
  sold_at: string;
}

export interface ClientDetail extends Client {
  purchases: ClientPurchase[];
}

// Работа в подборке клиента: status = shortlist (⭐) | sent (📤 отправлено на просмотр)
export interface SelectionItem {
  artwork_id: number;
  inventory_number: number;
  artwork_title: string | null;
  artist_name: string | null;
  primary_image: string | null;
  status: string;
  note: string | null;
  sale_price: number | null;
  currency: string;
  artwork_status: string;
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
  currency: string;
  notes: string | null;
  sold_at: string;
}

export interface DashboardSummary {
  total_sales: number;
  revenue_by_currency: Record<string, number>;
  referral_by_currency: Record<string, number>;
  purchase_by_currency?: Record<string, number>;
  margin_by_currency?: Record<string, number>;
  artworks_by_status: Record<string, number>;
  default_currency: string;
}

export interface AppSettings {
  default_currency: string;
  gallery_name: string;
  pdf_logo_url: string | null;
  pdf_watermark_enabled: boolean;
  pdf_watermark_text: string | null;
  currencies: Record<string, string>;
}

export const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  review: "На рассмотрении",
  for_sale: "В продаже",
  reserved: "Резерв",
  sold: "Продано",
  collection: "Коллекция",
  on_exhibition: "На выставке",
};

export const CLIENT_TYPE_LABELS: Record<string, string> = {
  buyer: "Покупатель",
  dealer: "Дилер",
  referral: "Реферал",
};
