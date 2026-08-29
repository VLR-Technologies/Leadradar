export interface CountryOption {
  code: string;
  name: string;
  requiresRegion: boolean;
}

export interface RegionOption {
  name: string;
}

export interface CityOption {
  id: number | null;
  name: string;
  region: string | null;
  district: string | null;
  displayName: string;
  latitude: number | null;
  longitude: number | null;
  population: number;
}
