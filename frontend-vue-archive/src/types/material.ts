export interface MaterialEntry {
  id: string;
  label: string;
  type: 'avatar' | 'audio' | 'video' | 'input' | 'log' | 'other';
  localPath: string;
  publicUrl: string;
  description?: string;
}
