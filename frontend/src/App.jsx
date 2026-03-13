import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const PANEL_BASE = import.meta.env.VITE_PANEL_BASE_URL || "https://panelpineapple.ambot24.ru";
const SUPPORT_URL = import.meta.env.VITE_SUPPORT_URL || "https://t.me/ambot24";

const TABS = [
  { id: "home", label: "Главная", title: "Главная" },
  { id: "wallet", label: "Кошелек", title: "Кошелек" },
  { id: "setup", label: "Настройка", title: "Настройка VPN" },
  { id: "referral", label: "Рефералы", title: "Реферальная система" },
  { id: "help", label: "Помощь", title: "Документы и помощь" },
];

const OS_OPTIONS = [
  { id: "windows", title: "Windows", app: "NekoRay" },
  { id: "iphone", title: "iPhone", app: "Streisand" },
  { id: "android", title: "Android", app: "v2rayNG" },
  { id: "macos", title: "macOS", app: "Streisand" },
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
  if (id === "home") return <svg className={cls} viewBox="0 0 24 24"><path d="M3 10.5L12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" /></svg>;
  if (id === "wallet") return <svg className={cls} viewBox="0 0 24 24"><path d="M3 8a3 3 0 0 1 3-3h11a2 2 0 0 1 2 2v1h1a2 2 0 0 1 2 2v6a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3z" /><circle cx="17" cy="13" r="1.7" /></svg>;
  if (id === "setup") return <svg className={cls} viewBox="0 0 24 24"><path d="M11 3h2l.5 2.1a7.9 7.9 0 0 1 1.7.7l1.9-1.1 1.4 1.4-1.1 1.9c.3.6.5 1.1.7 1.7L21 11v2l-2.1.5a7.9 7.9 0 0 1-.7 1.7l1.1 1.9-1.4 1.4-1.9-1.1c-.6.3-1.1.5-1.7.7L13 21h-2l-.5-2.1a7.9 7.9 0 0 1-1.7-.7l-1.9 1.1-1.4-1.4 1.1-1.9a7.9 7.9 0 0 1-.7-1.7L3 13v-2l2.1-.5c.2-.6.4-1.1.7-1.7L4.7 6.9l1.4-1.4L8 6.6c.6-.3 1.1-.5 1.7-.7z" /><circle cx="12" cy="12" r="3.2" /></svg>;
  if (id === "referral") return <svg className={cls} viewBox="0 0 24 24"><circle cx="8" cy="8" r="3" /><circle cx="16" cy="8" r="3" /><path d="M3 20a5 5 0 0 1 10 0zM11 20a5 5 0 0 1 10 0z" /></svg>;
  return <svg className={cls} viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 9 9 9 9 0 0 0-9-9zm1 14h-2v-2h2zm0-4h-2V7h2z" /></svg>;
}

function normalizeSubscriptionUrl(url) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${PANEL_BASE}${url}`;
  return url;
}

function onboardingTitle(step) {
  if (step === "welcome") return "Добро пожаловать в Pineapple VPN";
  if (step === "trial_offer") return "Попробуйте сервис бесплатно";
  if (step === "device_select") return "Выберите устройство";
  if (step === "install_app") return "Установите приложение";
  if (step === "get_config") return "Подключение готово";
  if (step === "complete") return "Настройка завершена";
  return "Готово";
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
  const [referralInfo, setReferralInfo] = useState(null);
  const [vpnConfig, setVpnConfig] = useState(null);

  const [onboarding, setOnboarding] = useState(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingInstruction, setOnboardingInstruction] = useState(null);
  const [onboardingConfig, setOnboardingConfig] = useState(null);
  const [consentChecked, setConsentChecked] = useState(false);

  const [topupAmount, setTopupAmount] = useState(100);
  const [docHtml, setDocHtml] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [selectedOs, setSelectedOs] = useState("windows");

  const authHeaders = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);
  const startParam = tg?.initDataUnsafe?.start_param || "";

  const request = async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      if (res.status === 401) {
        localStorage.removeItem("token");
        setToken(null);
        throw new Error("Сессия истекла. Выполняю повторную авторизацию...");
      }
      throw new Error(body?.detail || `HTTP ${res.status}`);
    }
    return res.json();
  };

  const refreshOnboardingState = async () => {
    if (!token) return null;
    const state = await request("/onboarding/state", { headers: authHeaders });
    setOnboarding(state);
    if (state?.os) setSelectedOs(state.os);
    setShowOnboarding(state?.step !== "done");
    return state;
  };

  const loadAll = async () => {
    if (!token) return;

    const results = await Promise.allSettled([
      request("/users/overview", { headers: authHeaders }),
      request("/subscriptions/status", { headers: authHeaders }),
      request("/subscriptions/plans", { headers: authHeaders }),
      request("/payments/history", { headers: authHeaders }),
      request("/referral/stats", { headers: authHeaders }),
      request("/referral/list", { headers: authHeaders }),
      request("/referral/info", { headers: authHeaders }),
      request("/onboarding/state", { headers: authHeaders }),
    ]);

    const [ov, st, pl, pay, rs, rl, ri, onb] = results;

    if (ov.status === "fulfilled") setOverview(ov.value);
    if (st.status === "fulfilled") setStatus(st.value);
    if (pl.status === "fulfilled") setPlans(pl.value);
    if (pay.status === "fulfilled") setPayments(pay.value);
    if (rs.status === "fulfilled") setReferralStats(rs.value);
    if (rl.status === "fulfilled") setReferralList(rl.value);
    if (ri.status === "fulfilled") setReferralInfo(ri.value);

    if (onb.status === "fulfilled") {
      setOnboarding(onb.value);
      if (onb.value?.os) setSelectedOs(onb.value.os);
      setShowOnboarding(onb.value?.step !== "done");
    }

    const fatal = results.find((item) => item.status === "rejected" && !String(item.reason?.message || "").includes("Сессия истекла"));
    if (fatal) throw fatal.reason;
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

  useEffect(() => {
    const loadInstructionIfNeeded = async () => {
      if (!showOnboarding || !token) return;
      if (onboarding?.step !== "install_app") return;
      try {
        const info = await request(`/onboarding/instructions?os=${selectedOs}`, { headers: authHeaders });
        setOnboardingInstruction(info);
      } catch (e) {
        setAuthError(String(e.message));
      }
    };

    loadInstructionIfNeeded();
  }, [showOnboarding, onboarding?.step, selectedOs, token]);

  useEffect(() => {
    if (tab !== "setup") return;
    if (!token) return;
    if (status?.status !== "active") return;
    if (vpnConfig?.subscription_url) return;
    loadVpnConfig().catch(() => {});
  }, [tab, token, status, vpnConfig]);

  const copy = async (text) => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    tg?.showPopup?.({ title: "Скопировано", message: "Текст скопирован", buttons: [{ type: "ok" }] });
  };

  const openDoc = async (name, title) => {
    const res = await fetch(`/docs/${name}.html`);
    const html = await res.text();
    const body = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    setDocTitle(title);
    setDocHtml(body ? body[1] : html);
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

  const startDeviceFlow = async () => {
    setLoading(true);
    try {
      await request("/onboarding/restart-device-flow", { method: "POST", headers: authHeaders });
      await refreshOnboardingState();
      setOnboardingConfig(null);
      setShowOnboarding(true);
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const onboardingAcceptTerms = async () => {
    if (!consentChecked) {
      setAuthError("Подтвердите согласие с правилами, чтобы продолжить.");
      return;
    }

    setLoading(true);
    try {
      const state = await request("/onboarding/accept-terms", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ accepted: true }),
      });
      setOnboarding(state);
      setShowOnboarding(true);
      await loadAll();
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const onboardingActivateTrial = async () => {
    setLoading(true);
    try {
      await request("/onboarding/activate-trial", { method: "POST", headers: authHeaders });
      await loadAll();
      await refreshOnboardingState();
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const onboardingSelectDevice = async () => {
    setLoading(true);
    try {
      const state = await request("/onboarding/device", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ os: selectedOs }),
      });
      setOnboarding(state);
      const info = await request(`/onboarding/instructions?os=${selectedOs}`, { headers: authHeaders });
      setOnboardingInstruction(info);
      await loadAll();
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const onboardingConfirmInstall = async () => {
    setLoading(true);
    try {
      const state = await request("/onboarding/confirm-install", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ os: selectedOs }),
      });
      setOnboarding(state);
      await loadAll();
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const onboardingGetConfig = async () => {
    setLoading(true);
    try {
      const config = await request("/onboarding/config", { method: "POST", headers: authHeaders });
      setOnboardingConfig(config);
      setVpnConfig({ subscription_url: config.subscription_url });
      await refreshOnboardingState();
      await loadAll();
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const onboardingComplete = async () => {
    setLoading(true);
    try {
      await request("/onboarding/complete", { method: "POST", headers: authHeaders });
      await loadAll();
      setShowOnboarding(false);
      setTab("home");
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const wallet = overview?.user?.wallet_balance_rub || 0;
  const subEndsAt = overview?.subscription?.ends_at;
  const subDaysLeft = daysLeft(subEndsAt);
  const hasPlanInfo = Boolean(status?.plan);

  const onboardingStep = onboarding?.step || "welcome";
  const onboardingStepIndex = onboarding?.step_index || 1;
  const onboardingTotal = onboarding?.total_steps || 6;

  const setupSubscriptionUrl = normalizeSubscriptionUrl(
    onboardingConfig?.subscription_url || vpnConfig?.subscription_url,
  );

  return (
    <div className="app-shell">
      <div className="bg-orb bg-orb-a" />
      <div className="bg-orb bg-orb-b" />

      <main className="app-main">
        {authError && <div className="alert">{authError}</div>}

        {showOnboarding && (
          <section className="onboarding-shell pulse-in">
            <article className="card onboarding-card">
              <div className="onboarding-progress-wrap">
                <div className="onboarding-progress-meta">Шаг {onboardingStepIndex} из {onboardingTotal}</div>
                <div className="onboarding-progress">
                  <span style={{ width: `${Math.round((onboardingStepIndex / onboardingTotal) * 100)}%` }} />
                </div>
              </div>

              <h2>{onboardingTitle(onboardingStep)}</h2>

              {onboardingStep === "welcome" && (
                <>
                  <p>
                    Pineapple VPN помогает безопасно пользоваться российскими сервисами из-за границы:
                    банки, Госуслуги, ЖКХ, рабочие и корпоративные системы.
                  </p>
                  <p className="muted">Сервис не предназначен для обхода блокировок и незаконной деятельности.</p>

                  <div className="doc-links inline-links onboarding-links">
                    <button className="link-btn" onClick={() => openDoc("terms", "Пользовательское соглашение")}>Соглашение</button>
                    <button className="link-btn" onClick={() => openDoc("privacy", "Политика конфиденциальности")}>Политика</button>
                    <button className="link-btn" onClick={() => openDoc("acceptable_use", "Правила использования")}>Правила</button>
                  </div>

                  <label className="consent-line">
                    <input type="checkbox" checked={consentChecked} onChange={(e) => setConsentChecked(e.target.checked)} />
                    <span>Я ознакомился и принимаю правила сервиса</span>
                  </label>

                  <button disabled={loading} onClick={onboardingAcceptTerms}>Продолжить</button>
                </>
              )}

              {onboardingStep === "trial_offer" && (
                <>
                  <p>
                    Вам доступен пробный период <strong>{onboarding?.trial_days || 3} дня</strong>
                    {(onboarding?.trial_days || 3) > 3 ? " по реферальной ссылке" : ""}.
                  </p>
                  <p className="muted">Полный доступ к подключению, чтобы проверить работу сервиса перед оплатой.</p>
                  <button disabled={loading} onClick={onboardingActivateTrial}>Попробовать бесплатно</button>
                </>
              )}

              {onboardingStep === "device_select" && (
                <>
                  <p>Выберите устройство, на котором хотите настроить подключение в первую очередь.</p>
                  <div className="os-grid">
                    {OS_OPTIONS.map((os) => (
                      <button
                        key={os.id}
                        className={`os-card ${selectedOs === os.id ? "active" : ""}`}
                        onClick={() => setSelectedOs(os.id)}
                      >
                        <span className="os-title">{os.title}</span>
                        <small>{os.app}</small>
                      </button>
                    ))}
                  </div>
                  <button disabled={loading} onClick={onboardingSelectDevice}>Продолжить</button>
                </>
              )}

              {onboardingStep === "install_app" && (
                <>
                  <p>
                    Установите приложение <strong>{onboardingInstruction?.app_name || "для выбранной ОС"}</strong>.
                    После установки вернитесь и подтвердите.
                  </p>
                  {onboardingInstruction?.download_url && (
                    <a className="download-link" href={onboardingInstruction.download_url} target="_blank" rel="noreferrer">
                      Скачать приложение
                    </a>
                  )}
                  <ol className="steps clean">
                    {(onboardingInstruction?.steps || []).map((line, idx) => (
                      <li key={idx} className="pending">{line}</li>
                    ))}
                  </ol>
                  <button disabled={loading} onClick={onboardingConfirmInstall}>Я установил приложение</button>
                </>
              )}

              {onboardingStep === "get_config" && (
                <>
                  <p>
                    Последний шаг: получите персональную ссылку подключения и импортируйте ее в установленное приложение.
                  </p>
                  {!setupSubscriptionUrl && (
                    <button disabled={loading} onClick={onboardingGetConfig}>Получить конфигурацию</button>
                  )}
                  {!!setupSubscriptionUrl && (
                    <div className="config-box">
                      <div className="config-item">
                        <label>Ссылка подключения</label>
                        <textarea readOnly value={setupSubscriptionUrl} rows={4} />
                      </div>
                      <button onClick={() => copy(setupSubscriptionUrl)}>Скопировать ссылку</button>
                    </div>
                  )}
                </>
              )}

              {(onboardingStep === "complete" || onboardingStep === "done") && (
                <>
                  <p>VPN готов к использованию. Вы можете открыть настройки, документацию или обратиться в поддержку.</p>
                  <div className="row wrap-row">
                    <button disabled={loading} onClick={onboardingComplete}>Перейти в приложение</button>
                    <button className="soft-btn" onClick={() => { setShowOnboarding(false); setTab("setup"); }}>Открыть настройки</button>
                    <button className="soft-btn" onClick={() => setTab("help")}>Документы</button>
                    <a className="soft-link" href={SUPPORT_URL} target="_blank" rel="noreferrer">Поддержка</a>
                  </div>
                </>
              )}
            </article>

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

        {!showOnboarding && tab === "home" && (
          <section className="page">
            <div className="hero">
              <div className="hero-title">Pineapple VPN</div>
              <p>Защищенный удаленный доступ к российским сервисам из-за границы</p>
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

            <article className="card tariffs-card">
              <h3>Тарифы</h3>
              <div className="grid two">
                {plans.map((plan) => (
                  <div className="price-card modern" key={plan.code}>
                    <div className="price-head">
                      <div className="price-name">{planRu(plan.code)}</div>
                      <div className="price-badge">{plan.duration_days} дней</div>
                    </div>
                    <div className="price-value">{plan.price_rub} ₽</div>
                    <p className="muted">Оплата из кошелька, продление без смены ключа.</p>
                    <button disabled={loading} onClick={() => buyPlan(plan.code)}>Оформить</button>
                  </div>
                ))}
              </div>
            </article>
          </section>
        )}

        {!showOnboarding && tab === "wallet" && (
          <section className="page">
            <article className="card wallet-balance">
              <h3>Кошелек</h3>
              <div className="balance-value">{wallet} ₽</div>
              <small>Используется для оплаты подписок</small>
            </article>

            <article className="card">
              <h3>Пополнение кошелька</h3>
              <div className="row">
                <input type="number" min="50" value={topupAmount} onChange={(e) => setTopupAmount(e.target.value)} />
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

        {!showOnboarding && tab === "setup" && (
          <section className="page">
            <article className="card">
              <h3>Ваша активная ссылка подключения</h3>
              <p className="muted">Этот ключ можно использовать на всех ваших устройствах.</p>
              {!setupSubscriptionUrl && (
                <button onClick={loadVpnConfig} disabled={loading || status?.status !== "active"}>Получить / обновить ключ</button>
              )}
              {status?.status !== "active" && <p className="muted">Для получения ключа активируйте пробный период или оплатите тариф.</p>}
              {!!setupSubscriptionUrl && (
                <div className="config-box">
                  <div className="config-item">
                    <label>Ссылка подключения</label>
                    <textarea readOnly value={setupSubscriptionUrl} rows={4} />
                  </div>
                  <button onClick={() => copy(setupSubscriptionUrl)}>Скопировать ключ</button>
                </div>
              )}
            </article>

            <article className="card">
              <h3>Подключить новое устройство</h3>
              <p className="muted">Запустите короткий мастер: выбор устройства, инструкция и импорт ссылки.</p>
              <button disabled={loading} onClick={startDeviceFlow}>Запустить мастер подключения</button>
            </article>
          </section>
        )}

        {!showOnboarding && tab === "referral" && (
          <section className="page">
            <article className="card">
              <h3>Реферальная система</h3>
              <p>Ссылка в Telegram-бот:</p>
              <div className="ref-link">{referralInfo?.bot_deep_link || referralStats?.bot_deep_link || "—"}</div>
              <div className="row">
                <button onClick={() => copy(referralInfo?.bot_deep_link || referralStats?.bot_deep_link)}>Скопировать ссылку</button>
              </div>
              <p>Готовое сообщение-приглашение:</p>
              <div className="ref-link">{referralInfo?.invite_message || referralStats?.invite_message || "—"}</div>
              <div className="row">
                <button onClick={() => copy(referralInfo?.invite_message || referralStats?.invite_message)}>Скопировать сообщение</button>
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

        {!showOnboarding && tab === "help" && (
          <section className="page">
            {!docHtml && (
              <article className="card">
                <h3>Документы</h3>
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

      {!showOnboarding && (
        <nav className="tabbar">
          {TABS.map((item) => (
            <button key={item.id} className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)} title={item.title} aria-label={item.label}>
              {iconForTab(item.id, tab === item.id)}
            </button>
          ))}
        </nav>
      )}
    </div>
  );
}
