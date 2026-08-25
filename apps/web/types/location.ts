export interface CountryOption {
  code: string;
  name: string;
  requiresRegion: boolean;
}

export interface RegionOption {
  name: string;
}

export interface CityOption {
  name: string;
  region: string | null;
}
