import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const TABS = [
  { id: "home", label: "Главная", title: "Главная" },
  { id: "wallet", label: "Кошелек", title: "Кошелек" },
  { id: "setup", label: "Настройка", title: "Настройка VPN" },
  { id: "referral", label: "Рефералы", title: "Реферальная система" },
  { id: "help", label: "Помощь", title: "Документы и помощь" },
];

function useTelegram() {
  return window.Telegram?.WebApp;
}

function formatDate(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function daysLeft(dt) {
  if (!dt) return null;
  const diffMs = new Date(dt).getTime() - Date.now();
  return Math.max(0, Math.ceil(diffMs / (24 * 60 * 60 * 1000)));
}

function statusRu(status) {
  if (status === "active") return "Активна";
  if (status === "expired") return "Истекла";
  return "Нет подписки";
}

function planRu(plan) {
  if (plan === "week") return "Неделя";
  if (plan === "month") return "Месяц";
  if (plan === "trial") return "Пробный период";
  return "—";
}

function operationMeta(item) {
  if (item.kind === "topup") return { title: "Пополнение ЮKassa", sign: "+", cls: "credit" };
  if (item.kind === "referral_bonus") return { title: "Реферальное начисление", sign: "+", cls: "credit" };
  if (item.kind === "subscription_debit") return { title: "Списание за тариф", sign: "-", cls: "debit" };
  return { title: "Операция", sign: "", cls: "neutral" };
}

function iconForTab(id, active) {
  const cls = `tab-icon ${active ? "active" : ""}`;
  if (id === "home") {
    return (
      <svg className={cls} viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 10.5L12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" />
      </svg>
    );
  }
  if (id === "wallet") {
    return (
      <svg className={cls} viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 8a3 3 0 0 1 3-3h11a2 2 0 0 1 2 2v1h1a2 2 0 0 1 2 2v6a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z" />
        <circle cx="17" cy="13" r="1.7" />
      </svg>
    );
  }
  if (id === "setup") {
    return (
      <svg className={cls} viewBox="0 0 24 24" aria-hidden="true">
        <path d="M11 3h2l.5 2.1a7.9 7.9 0 0 1 1.7.7l1.9-1.1 1.4 1.4-1.1 1.9c.3.6.5 1.1.7 1.7L21 11v2l-2.1.5a7.9 7.9 0 0 1-.7 1.7l1.1 1.9-1.4 1.4-1.9-1.1c-.6.3-1.1.5-1.7.7L13 21h-2l-.5-2.1a7.9 7.9 0 0 1-1.7-.7l-1.9 1.1-1.4-1.4 1.1-1.9a7.9 7.9 0 0 1-.7-1.7L3 13v-2l2.1-.5c.2-.6.4-1.1.7-1.7L4.7 6.9l1.4-1.4L8 6.6c.6-.3 1.1-.5 1.7-.7z" />
        <circle cx="12" cy="12" r="3.2" />
      </svg>
    );
  }
  if (id === "referral") {
    return (
      <svg className={cls} viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="8" cy="8" r="3" />
        <circle cx="16" cy="8" r="3" />
        <path d="M3 20a5 5 0 0 1 10 0zM11 20a5 5 0 0 1 10 0z" />
      </svg>
    );
  }
  return (
    <svg className={cls} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3a9 9 0 1 0 9 9 9 9 0 0 0-9-9zm1 14h-2v-2h2zm0-4h-2V7h2z" />
    </svg>
  );
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
  const [referralStats, setReferralStats] = useState(null);
  const [referralList, setReferralList] = useState([]);
  const [vpnConfig, setVpnConfig] = useState(null);

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
    const [ov, st, pl, pay, rs, rl] = await Promise.all([
      request("/users/overview", { headers: authHeaders }),
      request("/subscriptions/status", { headers: authHeaders }),
      request("/subscriptions/plans", { headers: authHeaders }),
      request("/payments/history", { headers: authHeaders }),
      request("/referral/stats", { headers: authHeaders }),
      request("/referral/list", { headers: authHeaders }),
    ]);
    setOverview(ov);
    setStatus(st);
    setPlans(pl);
    setPayments(pay);
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

  const copy = async (text) => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    tg?.showPopup?.({ title: "Скопировано", message: "Ссылка скопирована", buttons: [{ type: "ok" }] });
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

  const openDoc = async (name, title) => {
    const res = await fetch(`/docs/${name}.html`);
    const html = await res.text();
    const body = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    setDocTitle(title);
    setDocHtml(body ? body[1] : html);
  };

  const wallet = overview?.user?.wallet_balance_rub || 0;
  const trialAvailable = !!overview?.trial?.available;
  const subEndsAt = overview?.subscription?.ends_at;
  const subDaysLeft = daysLeft(subEndsAt);
  const hasPlanInfo = Boolean(status?.plan);

  const setupSteps = [
    { id: "trial", title: "Активируйте пробный период", done: overview?.trial?.active || !trialAvailable },
    { id: "wallet", title: "Пополните кошелек", done: wallet >= 50 },
    { id: "sub", title: "Оформите подписку", done: status?.status === "active" && !status?.trial },
    { id: "vpn", title: "Получите конфигурацию ВПН", done: !!vpnConfig?.subscription_url },
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
              <p>Защищенный удаленный доступ к российскому IP из-за границы</p>
              <div className="hero-status-grid">
                <div className="hero-status-item">
                  <span>Статус</span>
                  <strong>{statusRu(status?.status)}</strong>
                </div>
                {hasPlanInfo && (
                  <>
                    <div className="hero-status-item">
                      <span>Тариф</span>
                      <strong>{planRu(status?.plan)}</strong>
                    </div>
                    <div className="hero-status-item">
                      <span>Окончание</span>
                      <strong>{formatDate(subEndsAt)}</strong>
                    </div>
                    <div className="hero-status-item">
                      <span>Осталось</span>
                      <strong>{subDaysLeft === null ? "—" : `${subDaysLeft} дн.`}</strong>
                    </div>
                  </>
                )}
              </div>
            </div>

            {trialAvailable && (
              <article className="card accent">
                <h3>Пробный период</h3>
                <p>Доступно {overview?.trial?.days || 3} дн. Активируйте, когда будете готовы к настройке.</p>
                <button disabled={loading} onClick={activateTrial}>Активировать пробный период</button>
              </article>
            )}

            <article className="card">
              <h3>Тарифы</h3>
              <div className="grid two">
                {plans.map((plan) => (
                  <div className="price-card" key={plan.code}>
                    <div className="price-name">{planRu(plan.code)}</div>
                    <div className="price-value">{plan.price_rub} ₽</div>
                    <div className="price-meta">{plan.duration_days} дней</div>
                    <button disabled={loading} onClick={() => buyPlan(plan.code)}>Оформить</button>
                  </div>
                ))}
              </div>
            </article>
          </section>
        )}

        {tab === "wallet" && (
          <section className="page">
            <article className="card wallet-balance">
              <h3>Кошелек</h3>
              <div className="balance-value">{wallet} ₽</div>
              <small>Используется для оплаты подписок</small>
            </article>

            <article className="card">
              <h3>Пополнение кошелька</h3>
              <div className="row">
                <input
                  type="number"
                  min="50"
                  value={topupAmount}
                  onChange={(e) => setTopupAmount(e.target.value)}
                />
                <button disabled={loading} onClick={topup}>Пополнить</button>
              </div>
              <small>Минимальная сумма 50 ₽</small>
            </article>

            <article className="card">
              <h3>История операций</h3>
              <div className="ops-list">
                {payments.map((item) => {
                  const meta = operationMeta(item);
                  return (
                    <div key={item.id} className={`op-row ${meta.cls}`}>
                      <div>
                        <div className="op-title">{meta.title}</div>
                        <div className="op-date">{formatDate(item.created_at)}</div>
                      </div>
                      <div className="op-amount">{meta.sign}{item.amount_rub} ₽</div>
                    </div>
                  );
                })}
                {!payments.length && <div className="empty">Операций пока нет</div>}
              </div>
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
              <h3>Конфигурация VPN</h3>
              <p className="muted">Используйте ссылку в NekoRay или Streisand. В браузере открывать не нужно.</p>
              <button onClick={loadVpnConfig} disabled={loading}>Получить ссылку</button>
              {vpnConfig && (
                <div className="config-box">
                  <div className="config-item">
                    <label>Ссылка подписки</label>
                    <textarea readOnly value={normalizeSubscriptionUrl(vpnConfig.subscription_url)} rows={3} />
                  </div>
                  <div className="row">
                    <button onClick={() => copy(normalizeSubscriptionUrl(vpnConfig.subscription_url))}>
                      Скопировать конфигурацию VPN
                    </button>
                  </div>
                </div>
              )}
            </article>

            <div className="grid two">
              <article className="card">
                <h3>Windows (NekoRay)</h3>
                <ol>
                  <li>Установите NekoRay.</li>
                  <li>Добавьте профиль по конфигурацию VPN.</li>
                  <li>Выберите профиль и подключитесь.</li>
                </ol>
              </article>
              <article className="card">
                <h3>iPhone (Streisand)</h3>
                <ol>
                  <li>Установите Streisand.</li>
                  <li>Импортируйте профиль по конфигурации ВПН.</li>
                  <li>Включите VPN в приложении.</li>
                </ol>
              </article>
            </div>
          </section>
        )}

        {tab === "referral" && (
          <section className="page">
            <article className="card">
              <h3>Реферальная система</h3>
              <p>Ваша ссылка:</p>
              <div className="ref-link">{referralStats?.link || overview?.referral?.link || "—"}</div>
              <div className="row">
                <button onClick={() => copy(referralStats?.link || overview?.referral?.link)}>
                  Скопировать ссылку
                </button>
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
                {referralList.map((r, i) => (
                  <li key={`${r.invitee_id}-${i}`}>@{r.username || "-"} +{r.earned_rub} ₽</li>
                ))}
                {!referralList.length && <li>Рефералов пока нет</li>}
              </ul>
            </article>
          </section>
        )}

        {tab === "help" && (
          <section className="page">
            {!docHtml && (
              <article className="card">
                <h3>Документы</h3>
                <div className="doc-links">
                  <button className="link-btn" onClick={() => openDoc("terms", "Пользовательское соглашение")}>
                    Пользовательское соглашение
                  </button>
                  <button className="link-btn" onClick={() => openDoc("privacy", "Политика конфиденциальности")}>
                    Политика конфиденциальности
                  </button>
                  <button className="link-btn" onClick={() => openDoc("acceptable_use", "Правила использования")}>
                    Правила использования
                  </button>
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
          <button
            key={item.id}
            className={tab === item.id ? "active" : ""}
            onClick={() => setTab(item.id)}
            title={item.title}
            aria-label={item.label}
          >
            {iconForTab(item.id, tab === item.id)}
          </button>
        ))}
      </nav>
    </div>
  );
}
