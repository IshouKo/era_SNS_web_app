import { useEffect, useMemo, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import {
  Bell,
  Bookmark,
  Compass,
  Edit3,
  Heart,
  Home,
  Image,
  LogOut,
  Mail,
  MessageCircle,
  MoreHorizontal,
  Plane,
  Search,
  Send,
  Sparkles,
  Star,
  UserPlus,
} from 'lucide-react';
import {
  clearToken,
  createTweet,
  getMessages,
  getNotifications,
  getTimeline,
  getToken,
  likeTweet,
  login,
  me,
  replyTweet,
  sendMessage,
} from './api';
import type { DirectMessage, EraUser, NotificationItem, TimelineResponse, Tweet } from './types';

type View = 'home' | 'discover' | 'messages' | 'notifications';

const avatarFor = (user?: EraUser | null) =>
  user?.profile_image || `https://api.dicebear.com/9.x/avataaars/svg?seed=${user?.username ?? 'era'}`;

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin_password');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await login(username, password);
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ログインに失敗しました');
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="brand">
          <img src="/static/img/Eraicon.png" alt="" />
          Era
        </div>
        <h1>ログイン</h1>
        {error && <div className="flash danger">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="ユーザー名" />
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            placeholder="パスワード"
          />
          <button className="primary-button" type="submit">
            ログイン
          </button>
        </form>
        <p className="muted">Flask API の JWT 認証を使っています。</p>
      </section>
    </main>
  );
}

function Topbar({
  user,
  unreadCount,
  onView,
  onLogout,
}: {
  user: EraUser;
  unreadCount: number;
  onView: (view: View) => void;
  onLogout: () => void;
}) {
  return (
    <header className="topbar">
      <button className="brand reset-button" onClick={() => onView('home')}>
        <img src="/static/img/Eraicon.png" alt="" />
        Era
      </button>
      <label className="search-box">
        <Search size={22} />
        <input placeholder="興味のある内容を検索" />
      </label>
      <nav className="top-actions">
        <button className="icon-button" title="作成" onClick={() => onView('home')}>
          <Edit3 />
        </button>
        <button className="icon-button" title="メッセージ" onClick={() => onView('messages')}>
          <Mail />
        </button>
        <button className="icon-button badge-wrap" title="通知" onClick={() => onView('notifications')}>
          <Bell />
          {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
        </button>
        <img className="avatar" src={avatarFor(user)} alt={user.username} />
        <strong>{user.username}</strong>
        <button className="icon-button" title="ログアウト" onClick={onLogout}>
          <LogOut />
        </button>
      </nav>
    </header>
  );
}

function ProfileStrip({ user }: { user: EraUser }) {
  return (
    <>
      <section className="hero-banner" />
      <section className="profile-strip">
        <img className="avatar xl" src={avatarFor(user)} alt={user.username} />
        <div className="profile-copy">
          <div className="profile-name">
            {user.username} <span className="zone-pill">{user.age_zone}</span>
          </div>
          <p className="profile-bio">{user.bio || '日常を記録し、好きなことをシェア'}</p>
          <div className="stats">
            <span>フォロー {user.following_count}</span>
            <span>フォロワー {user.followers_count}</span>
          </div>
        </div>
        <button className="primary-button">プロフィールを編集</button>
      </section>
    </>
  );
}

function LeftRail({ activeView, onView, user }: { activeView: View; onView: (view: View) => void; user: EraUser }) {
  const items: Array<{ view: View; label: string; icon: ReactNode }> = [
    { view: 'home', label: 'ホーム', icon: <Home /> },
    { view: 'discover', label: '発見', icon: <Compass /> },
    { view: 'messages', label: 'メッセージ', icon: <MessageCircle /> },
    { view: 'notifications', label: '通知', icon: <Bell /> },
  ];

  return (
    <aside className="left-rail">
      <nav className="nav-list">
        {items.map((item) => (
          <button
            className={`nav-item ${activeView === item.view ? 'active' : ''}`}
            key={item.view}
            onClick={() => onView(item.view)}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
        <button className="nav-item">
          <Bookmark />
          ブックマーク
        </button>
        <button className="nav-item">
          <MoreHorizontal />
          もっと見る
        </button>
      </nav>
      <section className="space-panel">
        <span>あなたのスペース</span>
        <h3>{user.age_zone}</h3>
        <div className="stacked-avatars">
          {[user.username, 'haru', 'sora', 'mika'].map((seed) => (
            <img key={seed} src={`https://api.dicebear.com/9.x/avataaars/svg?seed=${seed}`} alt="" />
          ))}
        </div>
      </section>
    </aside>
  );
}

function Composer({ onCreated }: { onCreated: (tweet: Tweet) => void }) {
  const [body, setBody] = useState('');
  const [topic, setTopic] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try {
      const tweet = await createTweet(body.trim(), topic.trim() || undefined);
      onCreated(tweet);
      setBody('');
      setTopic('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        value={body}
        onChange={(event) => setBody(event.target.value)}
        maxLength={280}
        placeholder="最近の出来事やアイデアをシェアしよう？"
      />
      <div className="composer-actions">
        <div className="composer-tools">
          <button type="button">
            <Image size={20} />
            画像
          </button>
          <button type="button">
            <Sparkles size={20} />
            絵文字
          </button>
          <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="# 話題" />
        </div>
        <button className="primary-button" disabled={busy} type="submit">
          投稿
        </button>
      </div>
    </form>
  );
}

function PostCard({ tweet, onLiked }: { tweet: Tweet; onLiked: (tweet: Tweet) => void }) {
  const [reply, setReply] = useState('');
  const [replyOpen, setReplyOpen] = useState(false);

  async function handleLike() {
    onLiked(await likeTweet(tweet.id));
  }

  async function handleReply(event: FormEvent) {
    event.preventDefault();
    if (!reply.trim()) return;
    await replyTweet(tweet.id, reply.trim());
    setReply('');
    setReplyOpen(false);
  }

  return (
    <article className="post">
      <div className="post-head">
        <img className="avatar" src={avatarFor(tweet.author)} alt={tweet.author.username} />
        <div>
          <strong>{tweet.author.username}</strong>
          <span className="post-time">
            ・ {new Date(tweet.timestamp).toLocaleString('ja-JP', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
            ・ {tweet.author.age_zone}
          </span>
        </div>
        <button className="icon-button">
          <MoreHorizontal />
        </button>
      </div>
      <p className="post-body">{tweet.body}</p>
      {tweet.image_url && <img className="post-image" src={tweet.image_url} alt="投稿画像" />}
      <div className="post-actions">
        <button className={tweet.liked_by_me ? 'liked' : ''} onClick={handleLike}>
          <Heart size={21} fill={tweet.liked_by_me ? 'currentColor' : 'none'} /> {tweet.likes_count}
        </button>
        <button onClick={() => setReplyOpen((value) => !value)}>
          <MessageCircle size={21} /> {tweet.replies_count}
        </button>
        <button>
          <Send size={21} />
        </button>
      </div>
      {replyOpen && (
        <form className="reply-form" onSubmit={handleReply}>
          <input value={reply} onChange={(event) => setReply(event.target.value)} placeholder="返信を書く" />
          <button className="secondary-button" type="submit">
            送信
          </button>
        </form>
      )}
    </article>
  );
}

function Feed({ data, setData }: { data: TimelineResponse; setData: (data: TimelineResponse) => void }) {
  function replaceTweet(nextTweet: Tweet) {
    setData({ ...data, tweets: data.tweets.map((tweet) => (tweet.id === nextTweet.id ? nextTweet : tweet)) });
  }

  return (
    <main className="main-feed">
      <Composer onCreated={(tweet) => setData({ ...data, tweets: [tweet, ...data.tweets] })} />
      {data.tweets.length ? (
        data.tweets.map((tweet) => <PostCard key={tweet.id} tweet={tweet} onLiked={replaceTweet} />)
      ) : (
        <article className="post">
          <p className="post-body">まだ投稿がありません。最初の投稿をしてみましょう。</p>
        </article>
      )}
    </main>
  );
}

function RightRail({ data }: { data: TimelineResponse }) {
  const communities = useMemo(
    () => [
      { icon: '</>', label: 'プログラミング' },
      { icon: '♪', label: '音楽好き' },
      { icon: '☕', label: 'カフェ巡り' },
      { icon: <Plane size={30} />, label: '旅行記録' },
    ],
    [],
  );

  return (
    <aside className="right-rail">
      <section className="side-panel">
        <div className="side-head">
          <span>{data.selected_zone} トレンド</span>
          <button>もっと見る</button>
        </div>
        <div className="trend-card">
          <strong>{data.selected_zone}のトレンドをみんなでチェックしよう</strong>
          <button className="secondary-button">トレンドを見る</button>
        </div>
        {data.trends.map((trend) => (
          <p className="muted" key={trend.topic}>
            #{trend.topic} ・ {trend.count}件
          </p>
        ))}
      </section>
      <section className="side-panel">
        <div className="side-head">
          <span>おすすめユーザー</span>
          <button>もっと見る</button>
        </div>
        {data.suggested_users.map((user) => (
          <div className="user-row" key={user.id}>
            <img className="mini-avatar" src={avatarFor(user)} alt="" />
            <div>
              <strong>{user.username}</strong>
              <div className="muted">@{user.username}</div>
            </div>
            <button className="secondary-button">
              <UserPlus size={17} />
              フォロー
            </button>
          </div>
        ))}
      </section>
      <section className="side-panel">
        <div className="side-head">
          <span>人気のコミュニティ</span>
          <button>もっと見る</button>
        </div>
        <div className="community-grid">
          {communities.map((community) => (
            <div className="community" key={community.label}>
              <span>{community.icon}</span>
              <small>{community.label}</small>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

function NotificationsView({ items }: { items: NotificationItem[] }) {
  return (
    <main className="main-feed">
      <section className="post">
        <h2>通知</h2>
        {items.map((item) => (
          <div className="notification-row" key={item.id}>
            <div className="mini-avatar">
              <Bell size={20} />
            </div>
            <div>
              <strong>{item.kind}</strong>
              <p className="muted">{item.message}</p>
            </div>
          </div>
        ))}
        {!items.length && <p className="muted">通知はまだありません。</p>}
      </section>
    </main>
  );
}

function MessagesView({ messages, onSent }: { messages: DirectMessage[]; onSent: () => void }) {
  const [recipient, setRecipient] = useState('');
  const [body, setBody] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!recipient || !body) return;
    await sendMessage(recipient, body);
    setRecipient('');
    setBody('');
    onSent();
  }

  return (
    <main className="main-feed">
      <section className="post">
        <h2>メッセージ</h2>
        <form className="dm-form" onSubmit={submit}>
          <input value={recipient} onChange={(event) => setRecipient(event.target.value)} placeholder="宛先ユーザー名" />
          <textarea value={body} onChange={(event) => setBody(event.target.value)} placeholder="メッセージ" />
          <button className="primary-button" type="submit">
            送信
          </button>
        </form>
      </section>
      {messages.map((message) => (
        <article className="post" key={message.id}>
          <strong>
            {message.sender.username} → {message.recipient.username}
          </strong>
          <p className="post-body">{message.body}</p>
        </article>
      ))}
    </main>
  );
}

export function App() {
  const [user, setUser] = useState<EraUser | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [messages, setMessages] = useState<DirectMessage[]>([]);
  const [view, setView] = useState<View>('home');
  const [error, setError] = useState<string | null>(null);

  async function loadApp() {
    setError(null);
    try {
      const [mePayload, timelinePayload] = await Promise.all([me(), getTimeline()]);
      setUser(mePayload.user);
      setUnreadCount(mePayload.unread_count);
      setTimeline(timelinePayload);
    } catch (err) {
      clearToken();
      setUser(null);
      setTimeline(null);
      setError(err instanceof Error ? err.message : '読み込みに失敗しました');
    }
  }

  async function switchView(nextView: View) {
    setView(nextView);
    if (nextView === 'notifications') {
      setNotifications(await getNotifications());
      setUnreadCount(0);
    }
    if (nextView === 'messages') {
      setMessages(await getMessages());
    }
  }

  useEffect(() => {
    if (getToken()) {
      void loadApp();
    }
  }, []);

  if (!getToken() || !user || !timeline) {
    return <LoginScreen onLogin={() => void loadApp()} />;
  }

  return (
    <>
      <Topbar user={user} unreadCount={unreadCount} onView={(nextView) => void switchView(nextView)} onLogout={() => {
        clearToken();
        setUser(null);
      }} />
      <ProfileStrip user={user} />
      {error && <div className="global-error">{error}</div>}
      <div className="layout">
        <LeftRail activeView={view} onView={(nextView) => void switchView(nextView)} user={user} />
        {view === 'messages' ? (
          <MessagesView messages={messages} onSent={() => void switchView('messages')} />
        ) : view === 'notifications' ? (
          <NotificationsView items={notifications} />
        ) : (
          <Feed data={timeline} setData={setTimeline} />
        )}
        <RightRail data={timeline} />
      </div>
    </>
  );
}
