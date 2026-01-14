export type StageKey = 'avatar' | 'speech' | 'video';

export interface StageDefinition {
  id: StageKey;
  label: string;
  icon: string;
  color: string;
  weight: number;
}

export interface StageViewState {
  state: 'pending' | 'active' | 'done' | 'failed';
  description: string;
}
