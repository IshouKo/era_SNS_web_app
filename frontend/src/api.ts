import type { DirectMessage, EraUser, NotificationItem, TimelineResponse, Tweet } from './types';

const TOKEN_KEY = 'era_access_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(payload.message ?? response.statusText);
  }

  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<string> {
  const payload = await requestJson<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setToken(payload.access_token);
  return payload.access_token;
}

export async function me(): Promise<{ user: EraUser; unread_count: number }> {
  return requestJson('/api/me');
}

export async function getTimeline(): Promise<TimelineResponse> {
  return requestJson('/api/timeline');
}

export async function createTweet(body: string, topic?: string): Promise<Tweet> {
  const payload = await requestJson<{ tweet: Tweet }>('/api/tweets', {
    method: 'POST',
    body: JSON.stringify({ body, topic }),
  });
  return payload.tweet;
}

export async function likeTweet(tweetId: number): Promise<Tweet> {
  const payload = await requestJson<{ tweet: Tweet }>(`/api/tweets/${tweetId}/like`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
  return payload.tweet;
}

export async function replyTweet(tweetId: number, body: string): Promise<void> {
  await requestJson(`/api/tweets/${tweetId}/replies`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });
}

export async function getNotifications(): Promise<NotificationItem[]> {
  const payload = await requestJson<{ notifications: NotificationItem[] }>('/api/notifications');
  return payload.notifications;
}

export async function getMessages(): Promise<DirectMessage[]> {
  const payload = await requestJson<{ messages: DirectMessage[] }>('/api/messages');
  return payload.messages;
}

export async function sendMessage(recipient: string, body: string): Promise<void> {
  await requestJson('/api/messages', {
    method: 'POST',
    body: JSON.stringify({ recipient, body }),
  });
}
