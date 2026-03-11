import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

function useTelegram() {
  const tg = window.Telegram?.WebApp;
  return tg;
}

export default function App() {
  const tg = useTelegram();
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [status, setStatus] = useState(null);
  const [vpn, setVpn] = useState(null);
  const [adminMetrics, setAdminMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [referral, setReferral] = useState(null);
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
    const res = await fetch(`${API_BASE}/referral/info`, {
      headers: { ...authHeaders },
    });
    const data = await res.json();
    setReferral(data);
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

  useEffect(() => {
    if (token) {
      loadStatus();
      loadReferral();
      loadDevices();
      loadPayments();
      loadAdmin();
    }
  }, [token]);

  return (
    <div className="app">
      <header className="hero">
        <div className="brand">
          <div className="logo">P</div>
          <div>
            <h1>Pineapple VPN</h1>
            <p>Защищенный доступ к российскому IP из-за границы</p>
          </div>
        </div>
        <div className="status-card">
          <h3>Статус подписки</h3>
          <p>{status ? status.status : "загрузка..."}</p>
          {status?.ends_at && <p>До: {new Date(status.ends_at).toLocaleString("ru-RU")}</p>}
        </div>
      </header>

      <section className="plans">
        <h2>Тарифы</h2>
        <div className="plan-grid">
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

      <section className="vpn">
        <h2>VPN конфигурация</h2>
        <button onClick={loadVpn} disabled={loading}>Показать конфигурацию</button>
        {vpn && (
          <div className="vpn-box">
            <p><b>UUID:</b> {vpn.uuid}</p>
            <p><b>VLESS:</b> {vpn.vless_url}</p>
            <p><b>Subscription URL:</b> {vpn.subscription_url}</p>
          </div>
        )}
      </section>

      <section className="instructions">
        <h2>Инструкции подключения</h2>
        <div className="instruction-grid">
          <div>
            <h3>Windows (NekoRay)</h3>
            <ol>
              <li>Скачайте архив приложения по ссылке.</li>
              <li>Распакуйте архив и запустите NekoRay.</li>
              <li>Добавьте Subscription URL из раздела VPN конфигурации.</li>
            </ol>
          </div>
          <div>
            <h3>iPhone (Streisand)</h3>
            <ol>
              <li>Установите приложение Streisand из App Store.</li>
              <li>Откройте приложение и нажмите добавить профиль.</li>
              <li>Вставьте Subscription URL и сохраните профиль.</li>
            </ol>
          </div>
        </div>
      </section>

      <section className="referral">
        <h2>Реферальная система</h2>
        <p>Приглашайте друзей и получайте 10% от их платежей.</p>
        {referral && (
          <div className="vpn-box">
            <p><b>Ссылка:</b> {referral.referral_link}</p>
          </div>
        )}
      </section>

      <section className="devices">
        <h2>Устройства</h2>
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
      </section>

      <section className="payments">
        <h2>История платежей</h2>
        <ul>
          {payments.map((p) => (
            <li key={p.id}>{p.amount_rub} ₽ — {p.status}</li>
          ))}
        </ul>
      </section>

      {adminMetrics && (
        <section className="admin">
          <h2>Админ-панель</h2>
          <div className="admin-grid">
            <div>Пользователи: {adminMetrics.users_total}</div>
            <div>Активные подписки: {adminMetrics.active_subscriptions}</div>
            <div>Доход: {adminMetrics.revenue_total} ₽</div>
          </div>
        </section>
      )}

      <footer className="footer">
        <p>Сервис не предназначен для обхода блокировок. Используйте для легального доступа к российским сервисам из-за границы.</p>
      </footer>
    </div>
  );
}
