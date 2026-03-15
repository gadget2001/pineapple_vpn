import React, { useEffect, useMemo, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const PANEL_BASE = import.meta.env.VITE_PANEL_BASE_URL || "https://panelpineapple.ambot24.ru";
const SUPPORT_URL = import.meta.env.VITE_SUPPORT_URL || "https://t.me/AMBot_adm";
const LEGAL_DOCS_VERSION = import.meta.env.VITE_LEGAL_DOCS_VERSION || "2026-03-15";

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

const INTRO_SLIDES = [
  {
    badge: "Безопасность",
    title: "Безопасный доступ",
    text: "Доступ к важным российским сервисам при поездках и жизни за границей.",
    points: ["Стабильный доступ", "Защищенный канал", "Быстрая скорость"],
  },
  {
    badge: "Сервисы",
    title: "Работает со всеми сервисами РФ",
    text: "Подходит для финансовых, государственных и рабочих задач.",
    points: ["Банки", "Госуслуги", "ЖКХ-сервисы"],
  },
  {
    badge: "Быстрый старт",
    title: "Подключи за несколько минут",
    text: "Подробная инструкция поможет пройти все шаги без сложностей.",
    points: ["Пошаговый мастер", "Поддержка в один клик"],
  },
];

function useTelegram() {
  return window.Telegram?.WebApp;
}

function getStartPayloadFromUrl() {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  return params.get("startapp") || params.get("start") || "";
}

function getTopupIdFromUrl() {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("topup_id");
  if (!raw) return null;
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) return null;
  return value;
}

function clearTopupIdFromUrl() {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  url.searchParams.delete("topup_id");
  window.history.replaceState({}, "", url.toString());
}

function buildInviteMessage(link) {
  if (!link) return "";
  return [
    "🍍 Pineapple VPN",
    "",
    "Надежный доступ к российским сервисам из-за границы: банки, Госуслуги, ЖКХ и рабочие системы.",
    "",
    "🎁 По моему приглашению тебе доступно 7 дней бесплатно вместо 3.",
    "",
    "👇 Открывай бота и запускай MiniApp:",
    link,
  ].join("\n");
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
  if (item.kind === "topup") return { title: "Пополнение", sign: "+", cls: "credit" };
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

function parseSupportUsername(url) {
  if (!url) return "";
  const raw = String(url).trim();
  if (!raw) return "";
  if (raw.startsWith("@")) return raw.slice(1);
  try {
    const parsed = new URL(raw);
    if (!/^(t\.me|telegram\.me)$/i.test(parsed.hostname)) return "";
    const first = parsed.pathname.split("/").filter(Boolean)[0] || "";
    return first;
  } catch {
    return "";
  }
}

function isValidEmail(value) {
  const email = String(value || "").trim().toLowerCase();
  if (!email) return false;
  return /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$/.test(email);
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


function configInstructionByOs(os) {
  if (os === "iphone") {
    return [
      "Нажмите на этой странице <Скопировать кофигурацию>",
      "Откройте приложение Streisand.",
      "Нажмите значок <+> в правом верхнем углу меню.",
      "Затем нажмите <Добавить из буфера>",
      "ВПН настроен и его можно включить кнопкой <⏻>",
    ];
  }
  if (os === "windows") {
    return [
      "Откройте NekoRay.",
      "Добавьте subscription ссылку.",
      "Обновите конфигурации и включите подключение.",
    ];
  }
  if (os === "android") {
    return [
      "Откройте v2rayNG.",
      "Добавьте subscription ссылку.",
      "Обновите конфигурации и включите подключение.",
    ];
  }
  return [
    "Откройте клиент для подключения.",
    "Добавьте subscription ссылку.",
    "Обновите конфигурацию и включите подключение.",
  ];
}

export default function App() {
  const tg = useTelegram();

  const [token, setToken] = useState(localStorage.getItem("token"));
  const [tab, setTab] = useState("home");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isHydrating, setIsHydrating] = useState(true);

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
  const [configGenerating, setConfigGenerating] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [copyNotice, setCopyNotice] = useState("");
  const [showIntro, setShowIntro] = useState(false);
  const [introSlide, setIntroSlide] = useState(0);
  const [introTouchStartX, setIntroTouchStartX] = useState(null);
  const [consentChecked, setConsentChecked] = useState(false);

  const [topupAmount, setTopupAmount] = useState(100);
  const [receiptEmail, setReceiptEmail] = useState("");
  const [receiptEmailDraft, setReceiptEmailDraft] = useState("");
  const [receiptEmailSaving, setReceiptEmailSaving] = useState(false);
  const [docHtml, setDocHtml] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [selectedOs, setSelectedOs] = useState("windows");
  const alertRef = useRef(null);
  const docCardRef = useRef(null);
  const prevOnboardingStepRef = useRef(null);

  const authHeaders = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);
  const startParam = tg?.initDataUnsafe?.start_param || getStartPayloadFromUrl();
  const referralLink = referralInfo?.bot_deep_link || referralStats?.bot_deep_link || referralInfo?.referral_link || referralStats?.link || "";
  const referralInviteMessage = buildInviteMessage(referralLink);

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
    const email = overview?.user?.receipt_email || "";
    setReceiptEmail(email);
    setReceiptEmailDraft(email);
  }, [overview?.user?.receipt_email]);

  useEffect(() => {
    const auth = async () => {
      if (!tg?.initData) {
        setAuthError("Откройте приложение через кнопку в Telegram-боте.");
        setIsHydrating(false);
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
        setIsHydrating(false);
      }
    };

    auth();
  }, [tg, token, startParam]);

  useEffect(() => {
    if (!token) return;
    setIsHydrating(true);
    loadAll()
      .catch((e) => setAuthError(String(e.message)))
      .finally(() => setIsHydrating(false));
  }, [token]);

  useEffect(() => {
    if (!showOnboarding || onboarding?.step !== "welcome") {
      setShowIntro(false);
      return;
    }
    setShowIntro(true);
  }, [showOnboarding, onboarding?.step]);

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

  const copy = async (text, notice = "Ссылка скопирована") => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopyNotice(notice);
    window.setTimeout(() => setCopyNotice(""), 2000);
  };

  const shareInvite = async () => {
    const link = referralLink;
    if (!link) {
      setAuthError("Реферальная ссылка пока не загружена. Попробуйте через пару секунд.");
      return;
    }

    const shareBody = [
      "🍍 Pineapple VPN",
      "",
      "Надежный доступ к российским сервисам из-за границы: банки, Госуслуги, ЖКХ и рабочие системы.",
      "",
      "🎁 По моему приглашению тебе доступно 7 дней бесплатно вместо 3.",
      "",
      "👆 Ссылка для запуска бота — вверху сообщения.",
    ].join("\n");

    const shareText = shareBody.trim();
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(shareText)}`;

    try {
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(shareUrl);
        return;
      }

      if (navigator.share) {
        await navigator.share({ text: `${shareText}\n\n${link}` });
        return;
      }

      await copy(`${shareText}\n\n${link}`, "Приглашение скопировано");
      setAuthError("В вашем Telegram недоступна пересылка, текст скопирован.");
    } catch (e) {
      setAuthError(String(e?.message || "Не удалось открыть пересылку в Telegram"));
    }
  };

  const openDoc = async (name, title) => {
    const docPathBySlug = {
      "public-offer": "/docs/terms.html",
      "privacy-policy": "/docs/privacy.html",
      "acceptable-use": "/docs/acceptable_use.html",
    };
    const docPath = docPathBySlug[name] || `/docs/${name}.html`;

    const res = await fetch(docPath, { cache: "no-store" });
    if (!res.ok) throw new Error("Не удалось открыть документ");

    const html = await res.text();
    const styleBlocks = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)]
      .map((m) => m[0])
      .join("\n");
    const body = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    setDocTitle(title);
    setDocHtml(`${styleBlocks}${body ? body[1] : html}`);
  };

  const closeDoc = () => {
    setDocHtml("");
    setDocTitle("");
  };

  const startIntroFlow = () => {
    setShowIntro(false);
  };

  const introPrev = () => setIntroSlide((v) => (v - 1 + INTRO_SLIDES.length) % INTRO_SLIDES.length);
  const introNext = () => setIntroSlide((v) => (v + 1) % INTRO_SLIDES.length);
  const onIntroTouchStart = (e) => setIntroTouchStartX(e.changedTouches?.[0]?.clientX ?? null);
  const onIntroTouchEnd = (e) => {
    if (introTouchStartX === null) return;
    const endX = e.changedTouches?.[0]?.clientX ?? introTouchStartX;
    const delta = endX - introTouchStartX;
    if (Math.abs(delta) >= 40) {
      if (delta < 0) introNext();
      if (delta > 0) introPrev();
    }
    setIntroTouchStartX(null);
  };

  const saveReceiptEmail = async () => {
    const normalized = String(receiptEmailDraft || "").trim().toLowerCase();
    if (!isValidEmail(normalized)) {
      setAuthError("Укажите корректный email для получения кассовых чеков.");
      return;
    }

    setReceiptEmailSaving(true);
    try {
      const data = await request("/users/receipt-email", {
        method: "PUT",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalized }),
      });

      const savedEmail = data?.email || normalized;
      setReceiptEmail(savedEmail);
      setReceiptEmailDraft(savedEmail);
      setOverview((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          user: {
            ...(prev.user || {}),
            receipt_email: savedEmail,
          },
        };
      });
      setCopyNotice("Email для чеков сохранен");
      window.setTimeout(() => setCopyNotice(""), 2000);
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setReceiptEmailSaving(false);
    }
  };

  const topup = async () => {
    const normalizedEmail = String(receiptEmail || "").trim().toLowerCase();
    if (!isValidEmail(normalizedEmail)) {
      setAuthError("Укажите email для получения кассового чека перед оплатой.");
      return;
    }

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
    if (status?.status !== "active") {
      setAuthError("Повторная настройка доступна только при активном тарифе или пробном периоде.");
      return;
    }

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
        body: JSON.stringify({ accepted: true, docs_version: LEGAL_DOCS_VERSION }),
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
    if (status?.status !== "active") {
      setAuthError("Для получения конфигурации нужен активный тариф или пробный период.");
      return;
    }

    setConfigGenerating(true);
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
      setConfigGenerating(false);
      setLoading(false);
    }
  };

  const onboardingComplete = async () => {
    setLoading(true);
    try {
      await request("/onboarding/complete", { method: "POST", headers: authHeaders });
      await loadAll();
      setShowOnboarding(false);
      setShowQr(false);
      setTab("home");
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const closeRepeatOnboarding = async () => {
    setLoading(true);
    try {
      await request("/onboarding/cancel-device-flow", { method: "POST", headers: authHeaders });
      await loadAll();
      setShowOnboarding(false);
      setShowQr(false);
      setTab("setup");
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
  const hasActiveAccess = status?.status === "active";
  const hasReceiptEmail = Boolean(String(receiptEmail || "").trim());
  const isReceiptEmailDraftValid = isValidEmail(receiptEmailDraft);
  const canSaveReceiptEmail =
    isReceiptEmailDraftValid &&
    String(receiptEmailDraft || "").trim().toLowerCase() !== String(receiptEmail || "").trim().toLowerCase();

  const onboardingStep = onboarding?.step || "welcome";
  const onboardingStepIndex = onboarding?.step_index || 1;
  const onboardingTotal = onboarding?.total_steps || 6;
  const trialDays = onboarding?.trial_days || overview?.trial?.days || 3;
  const weekPlanPrice = plans.find((p) => p.code === "week")?.price_rub;
  const monthPlanPrice = plans.find((p) => p.code === "month")?.price_rub;
  const isRepeatDeviceFlow =
    Boolean(onboarding?.completed) &&
    ["device_select", "install_app", "get_config", "complete"].includes(onboardingStep);
  const repeatStepMap = {
    device_select: 1,
    install_app: 2,
    get_config: 3,
    complete: 4,
  };
  const progressStepIndex = isRepeatDeviceFlow ? (repeatStepMap[onboardingStep] || 1) : onboardingStepIndex;
  const progressTotal = isRepeatDeviceFlow ? 4 : onboardingTotal;

  const setupSubscriptionUrl = normalizeSubscriptionUrl(
    onboardingConfig?.subscription_url || vpnConfig?.subscription_url,
  );
  const configHelp = configInstructionByOs(selectedOs);

  const supportUsername = parseSupportUsername(SUPPORT_URL);
  const latestSubscriptionPayment = [...payments]
    .filter((item) => item?.kind === "subscription_debit" && item?.status === "paid")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  const supportSubscriptionStartedAt =
    status?.plan === "trial"
      ? overview?.trial?.activated_at || null
      : latestSubscriptionPayment?.created_at || null;
  const supportMessage = [
    "Здравствуйте! Нужна помощь с Pineapple VPN.",
    "",
    "Данные для быстрой диагностики:",
    `Telegram ID: ${overview?.user?.telegram_id || tg?.initDataUnsafe?.user?.id || "не найден"}`,
    `Username: @${overview?.user?.username || tg?.initDataUnsafe?.user?.username || "не указан"}`,
    `Статус подписки: ${statusRu(status?.status)}`,
    `Тариф: ${planRu(status?.plan)}`,
    `Оформлена: ${formatDate(supportSubscriptionStartedAt)}`,
    `Истекает: ${formatDate(status?.ends_at || overview?.subscription?.ends_at)}`,
    `Ключ VPN: ${setupSubscriptionUrl || "еще не получен"}`,
  ].join("\n");

  const supportChatUrl = supportUsername
    ? `https://t.me/${supportUsername}?text=${encodeURIComponent(supportMessage)}`
    : SUPPORT_URL;

  const openSupportChat = () => {
    if (tg?.openTelegramLink && supportChatUrl.startsWith("https://t.me/")) {
      tg.openTelegramLink(supportChatUrl);
      return;
    }
    window.open(supportChatUrl, "_blank", "noopener,noreferrer");
  };

  useEffect(() => {
    if (!authError) return;
    if (alertRef.current) {
      alertRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const timer = window.setTimeout(() => setAuthError(""), 5000);
    return () => window.clearTimeout(timer);
  }, [authError]);

  useEffect(() => {
    if (!docHtml) return;
    if (!docCardRef.current) return;
    docCardRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [docHtml]);

  useEffect(() => {
    if (!token) return;

    const topupId = getTopupIdFromUrl();
    if (!topupId) return;

    let cancelled = false;
    let timer = null;
    let attempts = 0;

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/payments/${topupId}/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) {
          if (!cancelled && attempts < 20) {
            attempts += 1;
            timer = window.setTimeout(poll, 3000);
          }
          return;
        }

        const data = await res.json();
        const st = data?.status;

        if (st === "paid") {
          if (!cancelled) {
            clearTopupIdFromUrl();
            setCopyNotice("Пополнение кошелька подтверждено");
            await loadAll();
          }
          return;
        }

        if (st === "canceled" || st === "failed") {
          if (!cancelled) {
            clearTopupIdFromUrl();
            setAuthError(st === "canceled" ? "Платеж был отменен." : "Платеж не завершен. Попробуйте снова.");
          }
          return;
        }

        if (!cancelled) {
          if (attempts === 0) {
            setAuthError("Платеж обрабатывается. Обычно подтверждение занимает несколько секунд.");
          }
          if (attempts < 20) {
            attempts += 1;
            timer = window.setTimeout(poll, 3000);
          } else {
            clearTopupIdFromUrl();
            setAuthError("Платеж еще обрабатывается. Обновите экран через минуту.");
          }
        }
      } catch {
        if (!cancelled && attempts < 20) {
          attempts += 1;
          timer = window.setTimeout(poll, 3000);
        }
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [token]);

  useEffect(() => {
    const prevStep = prevOnboardingStepRef.current;
    if (prevStep && onboardingStep !== prevStep && docHtml) {
      closeDoc();
    }
    prevOnboardingStepRef.current = onboardingStep;
  }, [onboardingStep, docHtml]);

  return (
    <div className="app-shell">
      <div className="bg-orb bg-orb-a" />
      <div className="bg-orb bg-orb-b" />

      <main className="app-main">
        {authError && <div ref={alertRef} className="alert">{authError}</div>}
        {copyNotice && <div className="toast-ok">{copyNotice}</div>}
        {isHydrating && (
          <section className="onboarding-shell pulse-in">
            <article className="card onboarding-card">
              <div className="config-loader-screen">
                <div className="loader-spinner" />
                <h3>Загружаем ваш кабинет</h3>
                <p>Проверяем авторизацию и восстанавливаем шаг настройки</p>
              </div>
            </article>
          </section>
        )}

        {!isHydrating && showOnboarding && showIntro && (
          <section className="onboarding-shell pulse-in">
            <article className="card intro-hero-card" onTouchStart={onIntroTouchStart} onTouchEnd={onIntroTouchEnd}>
              <div className="intro-illustration">
                <span className="intro-bubble a" />
                <span className="intro-bubble b" />
                <span className="intro-bubble c" />
                <span className="intro-bubble d" />
                <span className="intro-bubble e" />
                <span className="intro-bubble f" />
                <span className="intro-bubble g" />
                <span className="intro-bubble h" />
                <div className="intro-visual">
                  <strong>Pineapple VPN</strong>
                  <span>Защищенный доступ к важным сервисам из любой точки мира</span>
                </div>
              </div>
              <div className="intro-carousel">
                <button className="intro-arrow left" onClick={introPrev} aria-label="Предыдущий слайд">
                  <svg viewBox="0 0 24 24"><path d="M15 5 8 12l7 7" /></svg>
                </button>
                <div key={introSlide} className="intro-copy">
                  <article className="intro-slide-card">
                    <span className="intro-slide-badge">{INTRO_SLIDES[introSlide].badge}</span>
                    <h2>{INTRO_SLIDES[introSlide].title}</h2>
                    <p>{INTRO_SLIDES[introSlide].text}</p>
                    <ul className="intro-slide-points">
                      {INTRO_SLIDES[introSlide].points.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </article>
                </div>
                <button className="intro-arrow right" onClick={introNext} aria-label="Следующий слайд">
                  <svg viewBox="0 0 24 24"><path d="m9 5 7 7-7 7" /></svg>
                </button>
              </div>
              <div className="intro-dots">
                {INTRO_SLIDES.map((_, idx) => (
                  <button key={idx} className={`dot ${introSlide === idx ? "active" : ""}`} onClick={() => setIntroSlide(idx)} aria-label={`Слайд ${idx + 1}`} />
                ))}
              </div>
              <div className="intro-cards-grid">
                <div className="intro-chip-card trial-highlight">
                  <h4>{"Пробный период"}</h4>
                  <div className="value">{trialDays} {"дн."}</div>
                  <small>{trialDays > 3 ? "По реферальной ссылке" : "Стандартный доступ"}</small>
                </div>
                <div className="intro-chip-card">
                  <h4>{"Тарифы"}</h4>
                  <div className="tariff-line"><span>{"Неделя"}</span><strong>{weekPlanPrice != null ? `${weekPlanPrice} ₽` : "—"}</strong></div>
                  <div className="tariff-line"><span>{"Месяц"}</span><strong>{monthPlanPrice != null ? `${monthPlanPrice} ₽` : "—"}</strong></div>
                </div>
                <div className="intro-chip-card">
                  <h4>{"Способы оплаты"}</h4>
                  <div className="pay-icons"><span>{"СБП"}</span><span>{"Карта"}</span><span>SberPay</span></div>
                </div>
              </div>
              <button className="cta-main" onClick={startIntroFlow}>{"Начать пробный период"}</button>
            </article>
          </section>
        )}

        {!isHydrating && showOnboarding && !showIntro && (
          <section className="onboarding-shell pulse-in">
            <article className={`card onboarding-card ${isRepeatDeviceFlow ? "onboarding-card--with-close" : ""}`.trim()}>
              {isRepeatDeviceFlow && (
                <button
                  className="onboarding-close"
                  type="button"
                  onClick={closeRepeatOnboarding}
                  aria-label="Свернуть мастер"
                  title="Свернуть мастер"
                >
                  ×
                </button>
              )}
              <div className="onboarding-progress-wrap">
                <div className="onboarding-progress-meta">Шаг {progressStepIndex} из {progressTotal}</div>
                <div className="onboarding-progress">
                  <span style={{ width: `${Math.round((progressStepIndex / progressTotal) * 100)}%` }} />
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
                    <button className="link-btn" onClick={() => openDoc("public-offer", "Публичная оферта")}>Соглашение</button>
                    <button className="link-btn" onClick={() => openDoc("privacy-policy", "Политика конфиденциальности")}>Политика</button>
                    <button className="link-btn" onClick={() => openDoc("acceptable-use", "Правила использования")}>Правила</button>
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
                  {configGenerating && (
                    <div className="config-loader-screen">
                      <div className="loader-spinner" />
                      <h3>{"Готовим вашу конфигурацию VPN"}</h3>
                      <p>{"Это может занять несколько секунд"}</p>
                    </div>
                  )}

                  {!configGenerating && !setupSubscriptionUrl && (
                    <>
                      <p>{"Осталось получить персональную конфигурацию и добавить ее в приложение."}</p>
                      <button disabled={loading} onClick={onboardingGetConfig}>{"Получить конфигурацию"}</button>
                    </>
                  )}

                  {!configGenerating && !!setupSubscriptionUrl && (
                    <div className="vpn-ready-layout">
                      <h3>{"Ваш VPN готов"}</h3>
                      <p className="muted">{"Осталось добавить конфигурацию в приложение"}</p>

                      <div className="config-box">
                        <div className="config-item">
                          <label>{"Конфигурация VPN"}</label>
                          <textarea readOnly value={setupSubscriptionUrl} rows={4} />
                        </div>
                        <div className="row wrap-row">
                          <button onClick={() => copy(setupSubscriptionUrl)}>{"Скопировать конфигурацию"}</button>
                          <button className="soft-btn" onClick={() => setShowQr((v) => !v)}>{showQr ? "Скрыть QR код" : "Показать QR код"}</button>
                        </div>
                        {showQr && (
                          <div className="qr-wrap">
                            <QRCodeSVG value={setupSubscriptionUrl} size={210} level="M" includeMargin />
                          </div>
                        )}
                      </div>

                      <article className="mini-instruction">
                        <h4>{"Как подключить VPN"}</h4>
                        <ol className="steps clean">
                          {configHelp.map((line, idx) => (
                            <li key={idx} className="pending">{line}</li>
                          ))}
                        </ol>
                      </article>

                      <button onClick={onboardingComplete} disabled={loading}>{"Я добавил конфигурацию"}</button>

                      <div className="help-box">
                        <strong>{"Не получается подключиться?"}</strong>
                        <div className="row wrap-row">
                          <a className="soft-link" href={SUPPORT_URL} target="_blank" rel="noreferrer">{"Написать в поддержку"}</a>
                        </div>
                      </div>
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
              <article ref={docCardRef} className="card">
                <div className="row between">
                  <h3>{docTitle}</h3>
                  <button onClick={closeDoc}>Назад</button>
                </div>
                <div className="doc-view" dangerouslySetInnerHTML={{ __html: docHtml }} />
              </article>
            )}
          </section>
        )}

        {!isHydrating && !showOnboarding && tab === "home" && (
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

        {!isHydrating && !showOnboarding && tab === "wallet" && (
          <section className="page">
            <article className="card wallet-balance">
              <h3>Кошелек</h3>
              <div className="balance-value">{wallet} ₽</div>
              <small>Используется для оплаты подписок</small>
            </article>

            <article className="card receipt-email-card">
              <h3>Email для получения чеков</h3>
              <p className="muted">На этот адрес ЮKassa будет отправлять кассовые чеки после оплаты.</p>
              <div className="row receipt-email-row">
                <input
                  type="email"
                  value={receiptEmailDraft}
                  placeholder="name@example.com"
                  onChange={(e) => setReceiptEmailDraft(e.target.value)}
                />
                <button disabled={receiptEmailSaving || !canSaveReceiptEmail} onClick={saveReceiptEmail}>
                  {receiptEmailSaving ? "Сохраняем..." : "Сохранить"}
                </button>
              </div>
              {!hasReceiptEmail && <small className="warning-text">Перед оплатой нужно сохранить email для отправки кассового чека.</small>}
              {hasReceiptEmail && <small>Чеки отправляются на: {receiptEmail}</small>}
            </article>

            <article className="card">
              <h3>Пополнение кошелька</h3>
              <div className="row">
                <input type="number" min="50" value={topupAmount} onChange={(e) => setTopupAmount(e.target.value)} />
                <button disabled={loading || !hasReceiptEmail} onClick={topup}>Пополнить</button>
              </div>
              <small>Минимальная сумма 50 ₽</small>
              {!hasReceiptEmail && <small className="warning-text">Сначала укажите email в блоке выше.</small>}
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

        {!isHydrating && !showOnboarding && tab === "setup" && (
          <section className="page">
            <article className="card">
              <h3>Ваша активная ссылка подключения</h3>
              <p className="muted">Этот ключ можно использовать на всех ваших устройствах.</p>
              {hasActiveAccess && !setupSubscriptionUrl && (
                <button onClick={loadVpnConfig} disabled={loading || !hasActiveAccess}>Получить / обновить ключ</button>
              )}
              {status?.status !== "active" && <p className="muted">Для получения ключа активируйте пробный период или оплатите тариф.</p>}
              {hasActiveAccess && !!setupSubscriptionUrl && (
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
              <p className="muted">Поможем быстро настроить VPN на новом устройстве: выбор ОС, установка клиента и импорт конфигурации.</p>
              <p className="muted">Доступные ОС: Windows, iPhone, Android, macOS.</p>
              <button disabled={loading || !hasActiveAccess} onClick={startDeviceFlow}>Запустить мастер подключения</button>
            </article>
          </section>
        )}

        {!isHydrating && !showOnboarding && tab === "referral" && (
          <section className="page">
            <article className="card">
              <h3>Реферальная система</h3>
              <p className="muted">Друг получит 7 дней бесплатно вместо 3, а вы получаете 10% от любого пополнения друга, пока он пользуется VPN.</p>
              <p>Ссылка в Telegram-бот:</p>
              <div className="ref-link">{referralLink || "-"}</div>
              <div className="row">
                <button onClick={() => copy(referralLink)}>Скопировать ссылку</button>
              </div>
              <p>Готовое сообщение-приглашение:</p>
              <div className="ref-link">{referralInviteMessage || "-"}</div>
              <div className="row ref-share-row">
                <button onClick={() => copy(referralInviteMessage, "Приглашение скопировано")}>Скопировать приглашение</button>
                <button className="soft-btn" onClick={shareInvite}>Поделиться</button>
              </div>
              <div className="grid three">
                <div className="stat">Приглашено: {referralStats?.invited_count || 0}</div>
                <div className="stat">Начислено: {referralStats?.earned_rub || 0} ₽</div>
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

        {!isHydrating && !showOnboarding && tab === "help" && (
          <section className="page">
            {!docHtml && (
              <article className="card">
                <h3>{"Документы"}</h3>
                <div className="doc-links">
                  <button className="link-btn" onClick={() => openDoc("public-offer", "Публичная оферта")}>{"Пользовательское соглашение"}</button>
                  <button className="link-btn" onClick={() => openDoc("privacy-policy", "Политика конфиденциальности")}>{"Политика конфиденциальности"}</button>
                  <button className="link-btn" onClick={() => openDoc("acceptable-use", "Правила использования")}>{"Правила использования"}</button>
                </div>
              </article>
            )}
            {!!docHtml && (
              <article ref={docCardRef} className="card">
                <div className="row between">
                  <h3>{docTitle}</h3>
                  <button onClick={closeDoc}>{"Назад"}</button>
                </div>
                <div className="doc-view" dangerouslySetInnerHTML={{ __html: docHtml }} />
              </article>
            )}

            <article className="card support-card">
              <h3>{"Поддержка"}</h3>
              <p className="muted">{"Поможем с подключением, ошибками доступа, вопросами по оплате и продлению."}</p>
              <ul className="support-list">
                <li><strong>{"Когда обращаться:"}</strong> {"ежедневно, 10:00-22:00 МСК."}</li>
                <li><strong>{"Что решаем:"}</strong> {"настройка VPN, восстановление доступа, вопросы по подписке и платежам."}</li>
                <li><strong>{"Куда:"}</strong> <a href={SUPPORT_URL} target="_blank" rel="noreferrer">{SUPPORT_URL}</a></li>
              </ul>
              <div className="support-note">{"При нажатии кнопки откроется Telegram с уже заполненным сообщением: Telegram ID, статус подписки, даты и ссылка конфигурации."}</div>
              <button onClick={openSupportChat}>{"Написать в поддержку"}</button>
            </article>
          </section>
        )}
      </main>

      {!isHydrating && !showOnboarding && (
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

