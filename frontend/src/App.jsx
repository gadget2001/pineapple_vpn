import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

function useTelegram() {
  return window.Telegram?.WebApp;
}

export default function App() {
  const tg = useTelegram();
  const [token, setToken] = useState(localStorage.getItem("token"));
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

  const startParam = tg?.initDataUnsafe?.start_param || "";

  useEffect(() => {
    tg?.ready();
  }, [tg]);

  useEffect(() => {
    const authenticate = async () => {
      if (!tg?.initData) return;
      if (token) return;
      const res = await fetch(`${API_BASE}/auth/telegram`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          init_data: tg.initData,
          referral_code: startParam || null,
        }),
      });
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

  const loadOverview = async () => {
    const res = await fetch(`${API_BASE}/users/overview`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setOverview(data);
  };

  const loadStatus = async () => {
    const res = await fetch(`${API_BASE}/subscriptions/status`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setStatus(data);
  };

  const loadVpn = async () => {
    setLoading(true);
    const res = await fetch(`${API_BASE}/vpn/config`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setVpn(data);
    setLoading(false);
  };

  const loadReferral = async () => {
    const res = await fetch(`${API_BASE}/referral/stats`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setReferralStats(data);
  };

  const loadReferralList = async () => {
    const res = await fetch(`${API_BASE}/referral/list`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setReferralList(data);
  };

  const loadDevices = async () => {
    const res = await fetch(`${API_BASE}/users/devices`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setDevices(data);
  };

  const addDevice = async () => {
    if (!deviceName) return;
    await fetch(`${API_BASE}/users/devices`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ name: deviceName }),
    });
    setDeviceName("");
    loadDevices();
  };

  const loadPayments = async () => {
    const res = await fetch(`${API_BASE}/payments/history`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setPayments(data);
  };

  const createPayment = async (plan) => {
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
    if (res.ok) {
      const data = await res.json();
      setAdminMetrics(data);
    }
  };

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      tg?.showPopup?.({ title: "Скопировано", message: "Ссылка скопирована", buttons: [{ type: "ok" }] });
    } catch {
      // ignore
    }
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

  const subEnds = overview?.subscription?.ends_at
    ? new Date(overview.subscription.ends_at).toLocaleString("ru-RU")
    : "—";

  return (
    <div className="app">
      <header className="hero">
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
        </div>
      </header>

      <section className="section">
        <h2>Личный кабинет</h2>
        <div className="grid two">
          <div className="card">
            <h3>Профиль</h3>
            <p><b>Пользователь:</b> @{overview?.user?.username || "—"}</p>
            <p><b>Статус:</b> {overview?.subscription?.status || "—"}</p>
            <p><b>Тариф:</b> {overview?.subscription?.plan || "—"}</p>
            <p><b>Окончание:</b> {subEnds}</p>
          </div>
          <div className="card">
            <h3>Баланс и пробный период</h3>
            <p><b>Бонусы (рефералы):</b> {overview?.referral?.earned_rub || 0} ₽</p>
            <p><b>Пробный период:</b> {overview?.trial?.active ? "активен" : "нет"}</p>
            <p><b>Дней trial:</b> {overview?.trial?.days || 3}</p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Тарифы</h2>
        <div className="grid two">
          <div className="plan">
            <h3>Неделя</h3>
            <p className="price">74 ₽</p>
            <button onClick={() => createPayment("week")}>Купить</button>
          </div>
          <div className="plan">
            <h3>Месяц</h3>
            <p className="price">149 ₽</p>
            <button onClick={() => createPayment("month")}>Купить</button>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>VPN конфигурация</h2>
        <button onClick={loadVpn} disabled={loading}>Показать конфигурацию</button>
        {vpn && (
          <div className="card">
            <p><b>UUID:</b> {vpn.uuid}</p>
            <p><b>VLESS:</b> {vpn.vless_url}</p>
            <p><b>Subscription URL:</b> {vpn.subscription_url}</p>
            <div className="actions">
              <button onClick={() => copyText(vpn.subscription_url)}>Скопировать ссылку</button>
            </div>
          </div>
        )}
      </section>

      <section className="section">
        <h2>Инструкции подключения</h2>
        <div className="grid two">
          <div className="card">
            <h3>Windows (NekoRay)</h3>
            <ol>
              <li>Скачайте архив приложения по ссылке.</li>
              <li>Распакуйте архив и запустите NekoRay.</li>
              <li>Добавьте Subscription URL из раздела VPN конфигурации.</li>
            </ol>
          </div>
          <div className="card">
            <h3>iPhone (Streisand)</h3>
            <ol>
              <li>Установите приложение Streisand из App Store.</li>
              <li>Откройте приложение и нажмите добавить профиль.</li>
              <li>Вставьте Subscription URL и сохраните профиль.</li>
            </ol>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Реферальная система</h2>
        <div className="card">
          <p>Приглашайте друзей и получайте 10% от их платежей.</p>
          <p><b>Ваша ссылка:</b> {referralStats?.link || "—"}</p>
          <div className="actions">
            {referralStats?.link && <button onClick={() => copyText(referralStats.link)}>Скопировать</button>}
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

      <section className="section">
        <h2>Устройства</h2>
        <div className="card">
          <div className="device-form">
            <input
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              placeholder="Название устройства"
            />
            <button onClick={addDevice}>Добавить</button>
          </div>
          <ul>
            {devices.map((d) => (
              <li key={d.id}>{d.name}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="section">
        <h2>История платежей</h2>
        <div className="card">
          <ul>
            {payments.map((p) => (
              <li key={p.id}>{p.amount_rub} ₽ — {p.status}</li>
            ))}
            {!payments.length && <li>Платежей пока нет</li>}
          </ul>
        </div>
      </section>

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

      <section className="section">
        <h2>Документы</h2>
        <div className="card">
          <ul>
            <li><a href="/docs/terms.html" target="_blank" rel="noreferrer">Пользовательское соглашение</a></li>
            <li><a href="/docs/privacy.html" target="_blank" rel="noreferrer">Политика конфиденциальности</a></li>
            <li><a href="/docs/acceptable_use.html" target="_blank" rel="noreferrer">Правила использования</a></li>
          </ul>
        </div>
      </section>

      <footer className="footer">
        <p>Сервис не предназначен для обхода блокировок. Используйте для легального доступа к российским сервисам из-за границы.</p>
      </footer>
    </div>
  );
}