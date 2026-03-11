import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

function useTelegram() {
  return window.Telegram?.WebApp;
}

const TABS = [
  { id: "home", label: "Главная" },
  { id: "account", label: "Кабинет" },
  { id: "vpn", label: "VPN" },
  { id: "referral", label: "Рефералы" },
  { id: "help", label: "Помощь" },
];

export default function App() {
  const tg = useTelegram();
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [authError, setAuthError] = useState(null);
  const [overview, setOverview] = useState(null);
  const [status, setStatus] = useState(null);
  const [vpn, setVpn] = useState(null);
  const [adminMetrics, setAdminMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [referralStats, setReferralStats] = useState(null);
  const [referralList, setReferralList] = useState([]);
  const [devices, setDevices] = useState([]);
  const [deviceName, setDeviceName] = useState("");
  const [payments, setPayments] = useState([]);
  const [tab, setTab] = useState("home");
  const [doc, setDoc] = useState(null);
  const [docHtml, setDocHtml] = useState("");

  const startParam = tg?.initDataUnsafe?.start_param || "";

  useEffect(() => {
    tg?.ready();
  }, [tg]);

  useEffect(() => {
    const authenticate = async () => {
      if (!tg) {
        setAuthError("Откройте приложение в Telegram, иначе авторизация недоступна.");
        return;
      }
      if (!tg.initData) {
        setAuthError("Telegram не передал initData. Откройте MiniApp через кнопку бота.");
        return;
      }
      if (token) return;

      const res = await fetch(`${API_BASE}/auth/telegram`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          init_data: tg.initData,
          referral_code: startParam || null,
        }),
      });

      if (!res.ok) {
        let detail = "Не удалось пройти авторизацию.";
        try {
          const data = await res.json();
          if (data?.detail) detail = data.detail;
        } catch {
          // ignore
        }
        setAuthError(`Ошибка авторизации: ${detail}`);
        return;
      }

      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
      }
    };
    authenticate();
  }, [tg, token, startParam]);

  const authHeaders = useMemo(() => {
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  }, [token]);

  const safeFetch = async (path) => {
    if (!token) return null;
    const res = await fetch(`${API_BASE}${path}`, { headers: { ...authHeaders } });
    if (!res.ok) return null;
    return res.json();
  };

  const loadOverview = async () => setOverview(await safeFetch("/users/overview"));
  const loadStatus = async () => setStatus(await safeFetch("/subscriptions/status"));
  const loadDevices = async () => setDevices((await safeFetch("/users/devices")) || []);
  const loadPayments = async () => setPayments((await safeFetch("/payments/history")) || []);
  const loadReferral = async () => setReferralStats(await safeFetch("/referral/stats"));
  const loadReferralList = async () => setReferralList((await safeFetch("/referral/list")) || []);

  const loadVpn = async () => {
    setLoading(true);
    const data = await safeFetch("/vpn/config");
    setVpn(data);
    setLoading(false);
  };

  const addDevice = async () => {
    if (!deviceName || !token) return;
    await fetch(`${API_BASE}/users/devices`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ name: deviceName }),
    });
    setDeviceName("");
    loadDevices();
  };

  const createPayment = async (plan) => {
    if (!token) return;
    const res = await fetch(`${API_BASE}/payments/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ plan }),
    });
    const data = await res.json();
    if (data.confirmation_url) {
      window.location.href = data.confirmation_url;
    }
  };

  const loadAdmin = async () => {
    const res = await fetch(`${API_BASE}/admin/metrics`, { headers: { ...authHeaders } });
    if (res.ok) setAdminMetrics(await res.json());
  };

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      tg?.showPopup?.({ title: "Скопировано", message: "Ссылка скопирована", buttons: [{ type: "ok" }] });
    } catch {
      // ignore
    }
  };

  const openDoc = async (docId, title) => {
    const res = await fetch(`/docs/${docId}.html`);
    const html = await res.text();
    const body = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    setDoc({ id: docId, title });
    setDocHtml(body ? body[1] : html);
  };

  useEffect(() => {
    if (token) {
      loadOverview();
      loadStatus();
      loadReferral();
      loadReferralList();
      loadDevices();
      loadPayments();
      loadAdmin();
    }
  }, [token]);

  const referralLink =
    referralStats?.link ||
    (overview?.referral?.code ? `${window.location.origin}?startapp=${overview.referral.code}` : "");

  const renderHome = () => (
    <section className="section">
      <div className="hero">
        <div className="hero-text">
          <div className="logo">P</div>
          <h1>Pineapple VPN</h1>
          <p className="tagline">Защищенный доступ к российскому IP из-за границы</p>
          <div className="chips">
            <span>Банки и Госуслуги</span>
            <span>Налоги и ЖКХ</span>
            <span>Корпоративные системы</span>
          </div>
        </div>
        <div className="hero-card">
          <h3>Статус подписки</h3>
          <div className={`status-pill ${status?.status || "loading"}`}>
            {status ? status.status : "загрузка"}
          </div>
          {status?.ends_at && <p>До: {new Date(status.ends_at).toLocaleString("ru-RU")}</p>}
          {status?.trial && <p>Пробный период активен</p>}
          <button className="primary" onClick={() => setTab("vpn")}>Получить VPN</button>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Как получить доступ</h3>
          <ol>
            <li>Оформите подписку</li>
            <li>Скопируйте Subscription URL</li>
            <li>Подключитесь в приложении</li>
          </ol>
        </div>
        <div className="card">
          <h3>Тарифы</h3>
          <div className="price-grid">
            <div className="plan">
              <h4>Неделя</h4>
              <p className="price">74 ₽</p>
              <ul>
                <li>Доступ 7 дней</li>
                <li>1–2 устройства</li>
                <li>Поддержка</li>
              </ul>
              <button onClick={() => createPayment("week")}>Купить</button>
            </div>
            <div className="plan highlight">
              <div className="badge">Выгоднее</div>
              <h4>Месяц</h4>
              <p className="price">149 ₽</p>
              <ul>
                <li>Доступ 30 дней</li>
                <li>1–2 устройства</li>
                <li>Поддержка</li>
              </ul>
              <button onClick={() => createPayment("month")}>Купить</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  const renderAccount = () => (
    <section className="section">
      <h2>Личный кабинет</h2>
      <div className="grid two">
        <div className="card">
          <h3>Профиль</h3>
          <p><b>Пользователь:</b> @{overview?.user?.username || "—"}</p>
          <p><b>Статус:</b> {overview?.subscription?.status || "—"}</p>
          <p><b>Тариф:</b> {overview?.subscription?.plan || "—"}</p>
          <p><b>Окончание:</b> {overview?.subscription?.ends_at ? new Date(overview.subscription.ends_at).toLocaleString("ru-RU") : "—"}</p>
        </div>
        <div className="card">
          <h3>Баланс и пробный период</h3>
          <p><b>Бонусы (рефералы):</b> {overview?.referral?.earned_rub || 0} ₽</p>
          <p><b>Пробный период:</b> {overview?.trial?.active ? "активен" : "нет"}</p>
          <p><b>Дней trial:</b> {overview?.trial?.days || 3}</p>
        </div>
      </div>

      <div className="card">
        <h3>История платежей</h3>
        <ul>
          {payments.map((p) => (
            <li key={p.id}>{p.amount_rub} ₽ — {p.status}</li>
          ))}
          {!payments.length && <li>Платежей пока нет</li>}
        </ul>
      </div>

      <div className="card">
        <h3>Устройства</h3>
        <p className="muted">Добавляйте устройства, на которых вы используете VPN, чтобы удобно отслеживать подключения.</p>
        <div className="device-form">
          <input
            value={deviceName}
            onChange={(e) => setDeviceName(e.target.value)}
            placeholder="Например: iPhone 15 Pro"
          />
          <button onClick={addDevice}>Добавить</button>
        </div>
        <ul>
          {devices.map((d) => (
            <li key={d.id}>{d.name}</li>
          ))}
          {!devices.length && <li>Устройств пока нет</li>}
        </ul>
      </div>
    </section>
  );

  const renderVpn = () => (
    <section className="section">
      <h2>VPN доступ</h2>
      <div className="card">
        <h3>Ваши данные</h3>
        <p className="muted">После оплаты мы создаем профиль и выдаем Subscription URL.</p>
        <button onClick={loadVpn} disabled={loading}>Получить конфигурацию</button>
        {vpn && (
          <div className="card nested">
            <p><b>UUID:</b> {vpn.uuid}</p>
            <p><b>VLESS:</b> {vpn.vless_url}</p>
            <p><b>Subscription URL:</b> {vpn.subscription_url}</p>
            <div className="actions">
              <button onClick={() => copyText(vpn.subscription_url)}>Скопировать ссылку</button>
            </div>
          </div>
        )}
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Windows (NekoRay)</h3>
          <ol>
            <li>Скачайте архив приложения.</li>
            <li>Распакуйте и запустите NekoRay.</li>
            <li>Добавьте Subscription URL.</li>
          </ol>
        </div>
        <div className="card">
          <h3>iPhone (Streisand)</h3>
          <ol>
            <li>Установите Streisand из App Store.</li>
            <li>Откройте приложение и добавьте профиль.</li>
            <li>Вставьте Subscription URL и сохраните.</li>
          </ol>
        </div>
      </div>
    </section>
  );

  const renderReferral = () => (
    <section className="section">
      <h2>Реферальная система</h2>
      <div className="card">
        <p>Приглашайте друзей и получайте 10% от их платежей.</p>
        <p><b>Ваша ссылка:</b> {referralLink || "—"}</p>
        <div className="actions">
          {referralLink && <button onClick={() => copyText(referralLink)}>Скопировать</button>}
        </div>
        <div className="grid three">
          <div className="stat">Приглашено: {referralStats?.invited_count || 0}</div>
          <div className="stat">Начислено: {referralStats?.earned_rub || 0} ₽</div>
          <div className="stat">Комиссия: {referralStats?.commission_percent || 10}%</div>
        </div>
      </div>
      <div className="card">
        <h3>Ваши рефералы</h3>
        <ul>
          {referralList.map((r, idx) => (
            <li key={`${r.invitee_id}-${idx}`}>@{r.username || "—"} — {r.earned_rub} ₽</li>
          ))}
          {!referralList.length && <li>Пока нет рефералов</li>}
        </ul>
      </div>
    </section>
  );

  const renderHelp = () => (
    <section className="section">
      <h2>Помощь и документы</h2>
      {!doc && (
        <div className="card">
          <ul>
            <li><button className="link" onClick={() => openDoc("terms", "Пользовательское соглашение")}>Пользовательское соглашение</button></li>
            <li><button className="link" onClick={() => openDoc("privacy", "Политика конфиденциальности")}>Политика конфиденциальности</button></li>
            <li><button className="link" onClick={() => openDoc("acceptable_use", "Правила использования")}>Правила использования</button></li>
          </ul>
        </div>
      )}
      {doc && (
        <div className="card">
          <div className="doc-header">
            <button onClick={() => { setDoc(null); setDocHtml(""); }}>Назад</button>
            <h3>{doc.title}</h3>
          </div>
          <div className="doc-body" dangerouslySetInnerHTML={{ __html: docHtml }} />
        </div>
      )}
    </section>
  );

  return (
    <div className="app">
      {authError && (
        <div className="alert">
          {authError}
          <div className="muted" style={{ marginTop: 8 }}>
            initData length: {tg?.initData?.length || 0}
          </div>
        </div>
      )}

      {tab === "home" && renderHome()}
      {tab === "account" && renderAccount()}
      {tab === "vpn" && renderVpn()}
      {tab === "referral" && renderReferral()}
      {tab === "help" && renderHelp()}

      {adminMetrics && (
        <section className="section">
          <h2>Админ-панель</h2>
          <div className="grid three">
            <div className="stat">Пользователи: {adminMetrics.users_total}</div>
            <div className="stat">Активные подписки: {adminMetrics.active_subscriptions}</div>
            <div className="stat">Доход: {adminMetrics.revenue_total} ₽</div>
          </div>
        </section>
      )}

      <footer className="footer">
        <p>Сервис не предназначен для обхода блокировок. Используйте для легального доступа к российским сервисам из-за границы.</p>
      </footer>

      <nav className="tabbar">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={t.id === tab ? "active" : ""}
            onClick={() => { setDoc(null); setTab(t.id); }}
          >
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}