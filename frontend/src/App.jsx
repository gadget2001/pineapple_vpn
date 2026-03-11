import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const TABS = [
  { id: "home", label: "Home" },
  { id: "cabinet", label: "Cabinet" },
  { id: "setup", label: "Setup" },
  { id: "referral", label: "Referral" },
  { id: "help", label: "Help" },
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
        setAuthError("Open app from Telegram bot button.");
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
    tg?.showPopup?.({ title: "Copied", message: "Text copied", buttons: [{ type: "ok" }] });
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
    { id: "trial", title: "Activate trial", done: overview?.trial?.active || !trialAvailable },
    { id: "wallet", title: "Top up wallet", done: wallet >= 50 },
    { id: "sub", title: "Buy subscription", done: status?.status === "active" && !status?.trial },
    { id: "vpn", title: "Get VPN config", done: !!vpnConfig?.subscription_url },
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
              <p>Secure Russian IP access from abroad</p>
              <div className="hero-meta">
                <span className="pill">Wallet: {wallet} RUB</span>
                <span className="pill">Status: {status?.status || "none"}</span>
              </div>
            </div>
            <div className="grid two">
              <article className="card accent">
                <h3>Trial access</h3>
                <p>{trialAvailable ? `${overview?.trial?.days || 3} days available` : "Trial already used"}</p>
                <button disabled={!trialAvailable || loading} onClick={activateTrial}>Activate trial</button>
              </article>
              <article className="card">
                <h3>Wallet top-up</h3>
                <div className="row">
                  <input type="number" min="50" value={topupAmount} onChange={(e) => setTopupAmount(e.target.value)} />
                  <button disabled={loading} onClick={topup}>Top up</button>
                </div>
                <small>Minimum top-up is 50 RUB</small>
              </article>
            </div>
            <article className="card">
              <h3>Plans</h3>
              <div className="grid two">
                {plans.map((plan) => (
                  <div className="price-card" key={plan.code}>
                    <div className="price-name">{plan.title}</div>
                    <div className="price-value">{plan.price_rub} RUB</div>
                    <div className="price-meta">{plan.duration_days} days</div>
                    <button disabled={loading} onClick={() => buyPlan(plan.code)}>Buy</button>
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
                <h3>Profile</h3>
                <p>Username: @{overview?.user?.username || "-"}</p>
                <p>Subscription: {overview?.subscription?.plan || "-"}</p>
                <p>Ends at: {overview?.subscription?.ends_at ? new Date(overview.subscription.ends_at).toLocaleString() : "-"}</p>
              </article>
              <article className="card">
                <h3>Devices</h3>
                <div className="row">
                  <input value={deviceName} onChange={(e) => setDeviceName(e.target.value)} placeholder="Device name" />
                  <button onClick={addDevice}>Add</button>
                </div>
                <ul className="list">
                  {devices.map((d) => <li key={d.id}>{d.name}</li>)}
                  {!devices.length && <li>No devices yet</li>}
                </ul>
              </article>
            </div>
            <article className="card">
              <h3>Payment history</h3>
              <ul className="list">
                {payments.map((p) => <li key={p.id}>{p.kind} {p.amount_rub} RUB ({p.status})</li>)}
                {!payments.length && <li>No payments yet</li>}
              </ul>
            </article>
          </section>
        )}

        {tab === "setup" && (
          <section className="page">
            <article className="card">
              <h3>Step-by-step setup</h3>
              <ol className="steps">
                {setupSteps.map((s) => (
                  <li key={s.id} className={s.done ? "done" : "pending"}>{s.title}</li>
                ))}
              </ol>
            </article>
            <article className="card">
              <h3>VPN configuration</h3>
              <button onClick={loadVpnConfig} disabled={loading}>Get config</button>
              {vpnConfig && (
                <div className="config-box">
                  <p>UUID: {vpnConfig.uuid}</p>
                  <p>VLESS: {vpnConfig.vless_url}</p>
                  <p>Subscription URL: {vpnConfig.subscription_url}</p>
                  <div className="row">
                    <button onClick={() => copy(vpnConfig.subscription_url)}>Copy URL</button>
                  </div>
                </div>
              )}
            </article>
            <div className="grid two">
              <article className="card">
                <h3>Windows (NekoRay)</h3>
                <ol>
                  <li>Install NekoRay.</li>
                  <li>Paste Subscription URL.</li>
                  <li>Connect profile.</li>
                </ol>
              </article>
              <article className="card">
                <h3>iPhone (Streisand)</h3>
                <ol>
                  <li>Install Streisand.</li>
                  <li>Add profile by URL.</li>
                  <li>Enable connection.</li>
                </ol>
              </article>
            </div>
          </section>
        )}

        {tab === "referral" && (
          <section className="page">
            <article className="card">
              <h3>Referral stats</h3>
              <p>Link: {referralStats?.link || overview?.referral?.link || "-"}</p>
              <div className="row">
                <button onClick={() => copy(referralStats?.link || overview?.referral?.link)}>Copy referral link</button>
              </div>
              <div className="grid three">
                <div className="stat">Invited: {referralStats?.invited_count || 0}</div>
                <div className="stat">Earned: {referralStats?.earned_rub || 0} RUB</div>
                <div className="stat">Commission: {referralStats?.commission_percent || 10}%</div>
              </div>
            </article>
            <article className="card">
              <h3>Referrals</h3>
              <ul className="list">
                {referralList.map((r, i) => <li key={`${r.invitee_id}-${i}`}>@{r.username || "-"} +{r.earned_rub} RUB</li>)}
                {!referralList.length && <li>No referrals yet</li>}
              </ul>
            </article>
          </section>
        )}

        {tab === "help" && (
          <section className="page">
            {!docHtml && (
              <article className="card">
                <h3>Legal documents</h3>
                <div className="doc-links">
                  <button className="link-btn" onClick={() => openDoc("terms", "Terms")}>Terms</button>
                  <button className="link-btn" onClick={() => openDoc("privacy", "Privacy")}>Privacy</button>
                  <button className="link-btn" onClick={() => openDoc("acceptable_use", "Acceptable Use")}>Acceptable Use</button>
                </div>
              </article>
            )}
            {!!docHtml && (
              <article className="card">
                <div className="row between">
                  <h3>{docTitle}</h3>
                  <button onClick={() => { setDocHtml(""); setDocTitle(""); }}>Back</button>
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