export interface HistoryVideoItem {
  job_id: string;
  status: string;
  message?: string | null;
  video_url?: string | null;
  local_video_url?: string | null;
  public_video_path?: string | null;
  duration?: number | null;
  published_at?: string | null;
  file_size?: number | null;
}

export interface HistoryVideoResponse {
  count: number;
  items: HistoryVideoItem[];
}
