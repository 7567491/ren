export interface CharacterRecord {
  id: string;
  name: string;
  image_url?: string;
  thumbnail_url?: string;
  image_path?: string;
  appearance?: Record<string, string>;
  voice?: Record<string, any>;
  tags?: string[];
  source?: string;
  status?: string;
}
