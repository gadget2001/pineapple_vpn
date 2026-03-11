import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const TABS = [
  { id: "home", label: "Главная" },
  { id: "cabinet", label: "Кабинет" },
  { id: "setup", label: "Настройка" },
  { id: "referral", label: "Рефералы" },
  { id: "help", label: "Помощь" },
];

function useTelegram() {
  return window.Telegram?.WebApp;
}

export default function App() {
  const tg = useTelegram();
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [tab, setTab] = useState("home");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);

  const [overview, setOverview] = useState(null);
  const [status, setStatus] = useState(null);
  const [plans, setPlans] = useState([]);
  const [payments, setPayments] = useState([]);
  const [devices, setDevices] = useState([]);
  const [referralStats, setReferralStats] = useState(null);
  const [referralList, setReferralList] = useState([]);
  const [vpnConfig, setVpnConfig] = useState(null);

  const [deviceName, setDeviceName] = useState("");
  const [topupAmount, setTopupAmount] = useState(100);
  const [docHtml, setDocHtml] = useState("");
  const [docTitle, setDocTitle] = useState("");

  const authHeaders = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);
  const startParam = tg?.initDataUnsafe?.start_param || "";

  const request = async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body?.detail || `HTTP ${res.status}`);
    }
    return res.json();
  };

  const loadAll = async () => {
    if (!token) return;
    const [ov, st, pl, pay, dev, rs, rl] = await Promise.all([
      request("/users/overview", { headers: authHeaders }),
      request("/subscriptions/status", { headers: authHeaders }),
      request("/subscriptions/plans", { headers: authHeaders }),
      request("/payments/history", { headers: authHeaders }),
      request("/users/devices", { headers: authHeaders }),
      request("/referral/stats", { headers: authHeaders }),
      request("/referral/list", { headers: authHeaders }),
    ]);
    setOverview(ov);
    setStatus(st);
    setPlans(pl);
    setPayments(pay);
    setDevices(dev);
    setReferralStats(rs);
    setReferralList(rl);
  };

  useEffect(() => {
    const auth = async () => {
      if (!tg?.initData) {
        setAuthError("Откройте приложение через кнопку в Telegram-боте.");
        return;
      }
      if (token) return;
      try {
        const data = await request("/auth/telegram", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: tg.initData, referral_code: startParam || null }),
        });
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      } catch (e) {
        setAuthError(String(e.message));
      }
    };
    auth();
  }, [tg, token, startParam]);

  useEffect(() => {
    loadAll().catch((e) => setAuthError(String(e.message)));
  }, [token]);

  const activateTrial = async () => {
    setLoading(true);
    try {
      await request("/subscriptions/trial/activate", { method: "POST", headers: authHeaders });
      await loadAll();
      setTab("setup");
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const topup = async () => {
    setLoading(true);
    try {
      const data = await request("/payments/topup", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ amount_rub: Number(topupAmount) }),
      });
      if (data.confirmation_url) window.location.href = data.confirmation_url;
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const buyPlan = async (plan) => {
    setLoading(true);
    try {
      await request("/subscriptions/purchase", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      await loadAll();
      setTab("setup");
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const loadVpnConfig = async () => {
    setLoading(true);
    try {
      const data = await request("/vpn/config", { headers: authHeaders });
      setVpnConfig(data);
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const addDevice = async () => {
    if (!deviceName.trim()) return;
    await request("/users/devices", {
      method: "POST",
      headers: { ...authHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({ name: deviceName.trim() }),
    });
    setDeviceName("");
    const dev = await request("/users/devices", { headers: authHeaders });
    setDevices(dev);
  };

  const copy = async (text) => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    tg?.showPopup?.({ title: "Скопировано", message: "Текст скопирован", buttons: [{ type: "ok" }] });
  };

  const normalizeSubscriptionUrl = (url) => {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://")) return url;
    if (url.startsWith("/")) {
      const panelBase = import.meta.env.VITE_PANEL_BASE_URL || "https://panelpineapple.ambot24.ru";
      return `${panelBase}${url}`;
    }
    return url;
  };

  const readableVlessUrl = (url) => {
    if (!url) return "";
    try {
      return decodeURIComponent(url);
    } catch {
      return url;
    }
  };

  const openDoc = async (name, title) => {
    const res = await fetch(`/docs/${name}.html`);
    const html = await res.text();
    const body = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    setDocTitle(title);
    setDocHtml(body ? body[1] : html);
  };

  const wallet = overview?.user?.wallet_balance_rub || 0;
  const trialAvailable = overview?.trial?.available;

  const setupSteps = [
    { id: "trial", title: "Активировать пробный период", done: overview?.trial?.active || !trialAvailable },
    { id: "wallet", title: "Пополнить кошелек", done: wallet >= 50 },
    { id: "sub", title: "Оформить подписку", done: status?.status === "active" && !status?.trial },
    { id: "vpn", title: "Получить VPN конфиг", done: !!vpnConfig?.subscription_url },
  ];

  return (
    <div className="app-shell">
      <div className="bg-orb bg-orb-a" />
      <div className="bg-orb bg-orb-b" />

      <main className="app-main">
        {authError && <div className="alert">{authError}</div>}

        {tab === "home" && (
          <section className="page">
            <div className="hero">
              <div className="hero-title">Pineapple VPN</div>
              <p>Защищенный доступ к российскому IP из-за границы</p>
              <div className="hero-meta">
                <span className="pill">Кошелек: {wallet} ₽</span>
                <span className="pill">Статус: {status?.status || "нет"}</span>
              </div>
            </div>
            <div className="grid two">
              <article className="card accent">
                <h3>Пробный доступ</h3>
                <p>{trialAvailable ? `Доступно ${overview?.trial?.days || 3} дн.` : "Пробный период уже использован"}</p>
                <button disabled={!trialAvailable || loading} onClick={activateTrial}>Активировать trial</button>
              </article>
              <article className="card">
                <h3>Пополнение кошелька</h3>
                <div className="row">
                  <input type="number" min="50" value={topupAmount} onChange={(e) => setTopupAmount(e.target.value)} />
                  <button disabled={loading} onClick={topup}>Пополнить</button>
                </div>
                <small>Минимальное пополнение 50 ₽</small>
              </article>
            </div>
            <article className="card">
              <h3>Тарифы</h3>
              <div className="grid two">
                {plans.map((plan) => (
                  <div className="price-card" key={plan.code}>
                    <div className="price-name">{plan.code === "week" ? "Неделя" : "Месяц"}</div>
                    <div className="price-value">{plan.price_rub} ₽</div>
                    <div className="price-meta">{plan.duration_days} дней</div>
                    <button disabled={loading} onClick={() => buyPlan(plan.code)}>Оформить</button>
                  </div>
                ))}
              </div>
            </article>
          </section>
        )}

        {tab === "cabinet" && (
          <section className="page">
            <div className="grid two">
              <article className="card">
                <h3>Профиль</h3>
                <p>Пользователь: @{overview?.user?.username || "-"}</p>
                <p>Подписка: {overview?.subscription?.plan || "-"}</p>
                <p>До: {overview?.subscription?.ends_at ? new Date(overview.subscription.ends_at).toLocaleString() : "-"}</p>
              </article>
              <article className="card">
                <h3>Устройства</h3>
                <div className="row">
                  <input value={deviceName} onChange={(e) => setDeviceName(e.target.value)} placeholder="Название устройства" />
                  <button onClick={addDevice}>Добавить</button>
                </div>
                <ul className="list">
                  {devices.map((d) => <li key={d.id}>{d.name}</li>)}
                  {!devices.length && <li>Устройств пока нет</li>}
                </ul>
              </article>
            </div>
            <article className="card">
              <h3>История платежей</h3>
              <ul className="list">
                {payments.map((p) => <li key={p.id}>{p.kind} {p.amount_rub} ₽ ({p.status})</li>)}
                {!payments.length && <li>Платежей пока нет</li>}
              </ul>
            </article>
          </section>
        )}

        {tab === "setup" && (
          <section className="page">
            <article className="card">
              <h3>Пошаговая настройка</h3>
              <ol className="steps">
                {setupSteps.map((s) => (
                  <li key={s.id} className={s.done ? "done" : "pending"}>{s.title}</li>
                ))}
              </ol>
            </article>
            <article className="card">
              <h3>VPN конфигурация</h3>
              <button onClick={loadVpnConfig} disabled={loading}>Получить конфиг</button>
              {vpnConfig && (
                <div className="config-box">
                  <div className="config-item">
                    <label>UUID</label>
                    <textarea readOnly value={vpnConfig.uuid || ""} rows={2} />
                  </div>
                  <div className="config-item">
                    <label>VLESS ссылка</label>
                    <textarea readOnly value={readableVlessUrl(vpnConfig.vless_url)} rows={4} />
                  </div>
                  <div className="config-item">
                    <label>Subscription URL</label>
                    <textarea readOnly value={normalizeSubscriptionUrl(vpnConfig.subscription_url)} rows={3} />
                  </div>
                  <div className="row">
                    <button onClick={() => copy(normalizeSubscriptionUrl(vpnConfig.subscription_url))}>Скопировать Subscription URL</button>
                    <button onClick={() => copy(vpnConfig.vless_url)}>Скопировать VLESS</button>
                  </div>
                </div>
              )}
            </article>
            <div className="grid two">
              <article className="card">
                <h3>Windows (NekoRay)</h3>
                <ol>
                  <li>Установите NekoRay.</li>
                  <li>Вставьте Subscription URL.</li>
                  <li>Подключитесь.</li>
                </ol>
              </article>
              <article className="card">
                <h3>iPhone (Streisand)</h3>
                <ol>
                  <li>Установите Streisand.</li>
                  <li>Добавьте профиль по URL.</li>
                  <li>Включите VPN.</li>
                </ol>
              </article>
            </div>
          </section>
        )}

        {tab === "referral" && (
          <section className="page">
            <article className="card">
              <h3>Реферальная статистика</h3>
              <p>Ссылка: {referralStats?.link || overview?.referral?.link || "-"}</p>
              <div className="row">
                <button onClick={() => copy(referralStats?.link || overview?.referral?.link)}>Скопировать ссылку</button>
              </div>
              <div className="grid three">
                <div className="stat">Приглашено: {referralStats?.invited_count || 0}</div>
                <div className="stat">Начислено: {referralStats?.earned_rub || 0} ₽</div>
                <div className="stat">Комиссия: {referralStats?.commission_percent || 10}%</div>
              </div>
            </article>
            <article className="card">
              <h3>Список рефералов</h3>
              <ul className="list">
                {referralList.map((r, i) => <li key={`${r.invitee_id}-${i}`}>@{r.username || "-"} +{r.earned_rub} ₽</li>)}
                {!referralList.length && <li>Рефералов пока нет</li>}
              </ul>
            </article>
          </section>
        )}

        {tab === "help" && (
          <section className="page">
            {!docHtml && (
              <article className="card">
                <h3>Юридические документы</h3>
                <div className="doc-links">
                  <button className="link-btn" onClick={() => openDoc("terms", "Пользовательское соглашение")}>Пользовательское соглашение</button>
                  <button className="link-btn" onClick={() => openDoc("privacy", "Политика конфиденциальности")}>Политика конфиденциальности</button>
                  <button className="link-btn" onClick={() => openDoc("acceptable_use", "Правила использования")}>Правила использования</button>
                </div>
              </article>
            )}
            {!!docHtml && (
              <article className="card">
                <div className="row between">
                  <h3>{docTitle}</h3>
                  <button onClick={() => { setDocHtml(""); setDocTitle(""); }}>Назад</button>
                </div>
                <div className="doc-view" dangerouslySetInnerHTML={{ __html: docHtml }} />
              </article>
            )}
          </section>
        )}
      </main>

      <nav className="tabbar">
        {TABS.map((item) => (
          <button key={item.id} className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>{item.label}</button>
        ))}
      </nav>
    </div>
  );
}
