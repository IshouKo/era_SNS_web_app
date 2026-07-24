export type EraUser = {
  id: number;
  username: string;
  age_zone: string;
  bio: string | null;
  profile_image: string | null;
  following_count: number;
  followers_count: number;
  role: string;
};

export type Tweet = {
  id: number;
  body: string;
  timestamp: string;
  author: EraUser;
  image_url: string | null;
  topic: string | null;
  age_zone: string;
  likes_count: number;
  replies_count: number;
  liked_by_me: boolean;
  moderation_status: string;
};

export type Trend = {
  topic: string;
  count: number;
};

export type NotificationItem = {
  id: number;
  kind: string;
  message: string;
  created_at: string;
  is_read: boolean;
};

export type DirectMessage = {
  id: number;
  sender: EraUser;
  recipient: EraUser;
  body: string;
  created_at: string;
  moderation_status: string;
};

export type TimelineResponse = {
  tweets: Tweet[];
  trends: Trend[];
  suggested_users: EraUser[];
  selected_zone: string;
};
