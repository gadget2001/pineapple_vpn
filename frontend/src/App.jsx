import React, { useEffect, useMemo, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";
const PANEL_BASE = import.meta.env.VITE_PANEL_BASE_URL || "https://panelpineapple.ambot24.ru";
const SUPPORT_URL = import.meta.env.VITE_SUPPORT_URL || "https://t.me/AMBot_adm";
const LEGAL_DOCS_VERSION = import.meta.env.VITE_LEGAL_DOCS_VERSION || "2026-03-15";
const BOT_USERNAME = import.meta.env.VITE_BOT_USERNAME || "pineapple_AMBot";

const TABS = [
  { id: "home", label: "Р“Р»Р°РІРЅР°СЏ", title: "Р“Р»Р°РІРЅР°СЏ" },
  { id: "wallet", label: "РљРѕС€РµР»РµРє", title: "РљРѕС€РµР»РµРє" },
  { id: "setup", label: "РќР°СЃС‚СЂРѕР№РєР°", title: "РќР°СЃС‚СЂРѕР№РєР° VPN" },
  { id: "referral", label: "Р РµС„РµСЂР°Р»С‹", title: "Р РµС„РµСЂР°Р»СЊРЅР°СЏ СЃРёСЃС‚РµРјР°" },
  { id: "help", label: "РџРѕРјРѕС‰СЊ", title: "Р”РѕРєСѓРјРµРЅС‚С‹ Рё РїРѕРјРѕС‰СЊ" },
];

const OS_OPTIONS = [
  { id: "windows", title: "Windows", app: "Clash Meta / Mihomo" },
  { id: "iphone", title: "iPhone", app: "Happ" },
  { id: "android", title: "Android", app: "Clash Meta / Mihomo" },
  { id: "macos", title: "macOS", app: "Clash Meta / Mihomo" },
  { id: "linux", title: "Linux", app: "Clash Meta / Mihomo" },
];

const INTRO_SLIDES = [
  {
    badge: "Р‘РµР·РѕРїР°СЃРЅРѕСЃС‚СЊ",
    title: "Р‘РµР·РѕРїР°СЃРЅС‹Р№ РґРѕСЃС‚СѓРї",
    text: "Р”РѕСЃС‚СѓРї Рє РІР°Р¶РЅС‹Рј СЂРѕСЃСЃРёР№СЃРєРёРј СЃРµСЂРІРёСЃР°Рј РїСЂРё РїРѕРµР·РґРєР°С… Рё Р¶РёР·РЅРё Р·Р° РіСЂР°РЅРёС†РµР№.",
    points: ["РЎС‚Р°Р±РёР»СЊРЅС‹Р№ РґРѕСЃС‚СѓРї", "Р—Р°С‰РёС‰РµРЅРЅС‹Р№ РєР°РЅР°Р»", "Р‘С‹СЃС‚СЂР°СЏ СЃРєРѕСЂРѕСЃС‚СЊ"],
  },
  {
    badge: "РЎРµСЂРІРёСЃС‹",
    title: "Р Р°Р±РѕС‚Р°РµС‚ СЃРѕ РІСЃРµРјРё СЃРµСЂРІРёСЃР°РјРё Р Р¤",
    text: "РџРѕРґС…РѕРґРёС‚ РґР»СЏ С„РёРЅР°РЅСЃРѕРІС‹С…, РіРѕСЃСѓРґР°СЂСЃС‚РІРµРЅРЅС‹С… Рё СЂР°Р±РѕС‡РёС… Р·Р°РґР°С‡.",
    points: ["Р‘Р°РЅРєРё", "Р“РѕСЃСѓСЃР»СѓРіРё", "Р–РљРҐ-СЃРµСЂРІРёСЃС‹"],
  },
  {
    badge: "Р‘С‹СЃС‚СЂС‹Р№ СЃС‚Р°СЂС‚",
    title: "РџРѕРґРєР»СЋС‡Рё Р·Р° РЅРµСЃРєРѕР»СЊРєРѕ РјРёРЅСѓС‚",
    text: "РџРѕРґСЂРѕР±РЅР°СЏ РёРЅСЃС‚СЂСѓРєС†РёСЏ РїРѕРјРѕР¶РµС‚ РїСЂРѕР№С‚Рё РІСЃРµ С€Р°РіРё Р±РµР· СЃР»РѕР¶РЅРѕСЃС‚РµР№.",
    points: ["РџРѕС€Р°РіРѕРІС‹Р№ РјР°СЃС‚РµСЂ", "РџРѕРґРґРµСЂР¶РєР° РІ РѕРґРёРЅ РєР»РёРє"],
  },
];

const INSTRUCTION_IMAGE_FOLDERS = {
  windows: ["Windows", "windows"],
  iphone: ["Iphone", "iPhone", "iphone"],
  android: ["Android", "android"],
  macos: ["macOS", "MacOS", "macos"],
  linux: ["Linux", "linux"],
};

const MAX_INSTRUCTION_IMAGES = 10;

function checkImageExists(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

async function loadInstructionImages(os) {
  const folders = INSTRUCTION_IMAGE_FOLDERS[os] || [];
  for (const folder of folders) {
    const found = [];
    for (let i = 1; i <= MAX_INSTRUCTION_IMAGES; i += 1) {
      const src = `/docs/img/Instructions/${folder}/${i}.png`;
      // no-cache query so newly uploaded screenshots become visible without rebuild
      const cacheBusted = `${src}?v=${Date.now()}`;
      // eslint-disable-next-line no-await-in-loop
      const exists = await checkImageExists(cacheBusted);
      if (exists) {
        found.push(src);
      }
    }
    if (found.length > 0) return found;
  }
  return [];
}

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
    "рџЌЌ Pineapple VPN",
    "",
    "РќР°РґРµР¶РЅС‹Р№ РґРѕСЃС‚СѓРї Рє СЂРѕСЃСЃРёР№СЃРєРёРј СЃРµСЂРІРёСЃР°Рј РёР·-Р·Р° РіСЂР°РЅРёС†С‹: Р±Р°РЅРєРё, Р“РѕСЃСѓСЃР»СѓРіРё, Р–РљРҐ Рё СЂР°Р±РѕС‡РёРµ СЃРёСЃС‚РµРјС‹.",
    "",
    "рџЋЃ РџРѕ РјРѕРµРјСѓ РїСЂРёРіР»Р°С€РµРЅРёСЋ С‚РµР±Рµ РґРѕСЃС‚СѓРїРЅРѕ 7 РґРЅРµР№ Р±РµСЃРїР»Р°С‚РЅРѕ РІРјРµСЃС‚Рѕ 3.",
    "",
    "рџ‘‡ РћС‚РєСЂС‹РІР°Р№ Р±РѕС‚Р° Рё Р·Р°РїСѓСЃРєР°Р№ MiniApp:",
    link,
  ].join("\n");
}

function formatDate(dt) {
  if (!dt) return "вЂ”";
  return new Date(dt).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function addDays(dateValue, days) {
  const base = new Date(dateValue);
  return new Date(base.getTime() + days * 24 * 60 * 60 * 1000);
}

function daysLeft(dt) {
  if (!dt) return null;
  const diffMs = new Date(dt).getTime() - Date.now();
  return Math.max(0, Math.ceil(diffMs / (24 * 60 * 60 * 1000)));
}

function statusRu(status) {
  if (status === "active") return "РђРєС‚РёРІРЅР°";
  if (status === "expired") return "РСЃС‚РµРєР»Р°";
  return "РќРµС‚ РїРѕРґРїРёСЃРєРё";
}

function planRu(plan) {
  if (plan === "week") return "РќРµРґРµР»СЏ";
  if (plan === "month") return "РњРµСЃСЏС†";
  if (plan === "trial") return "РџСЂРѕР±РЅС‹Р№ РїРµСЂРёРѕРґ";
  return "вЂ”";
}

function operationMeta(item) {
  if (item.kind === "topup") return { title: "РџРѕРїРѕР»РЅРµРЅРёРµ", sign: "+", cls: "credit" };
  if (item.kind === "referral_bonus") return { title: "Р РµС„РµСЂР°Р»СЊРЅРѕРµ РЅР°С‡РёСЃР»РµРЅРёРµ", sign: "+", cls: "credit" };
  if (item.kind === "subscription_debit") return { title: "РЎРїРёСЃР°РЅРёРµ Р·Р° С‚Р°СЂРёС„", sign: "-", cls: "debit" };
  return { title: "РћРїРµСЂР°С†РёСЏ", sign: "", cls: "neutral" };
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
  if (step === "welcome") return "Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ Pineapple VPN";
  if (step === "trial_offer") return "РџРѕРїСЂРѕР±СѓР№С‚Рµ СЃРµСЂРІРёСЃ Р±РµСЃРїР»Р°С‚РЅРѕ";
  if (step === "device_select") return "Р’С‹Р±РµСЂРёС‚Рµ СѓСЃС‚СЂРѕР№СЃС‚РІРѕ";
  if (step === "install_app") return "РЈСЃС‚Р°РЅРѕРІРёС‚Рµ РїСЂРёР»РѕР¶РµРЅРёРµ";
  if (step === "get_config") return "РџРѕРґРєР»СЋС‡РµРЅРёРµ РіРѕС‚РѕРІРѕ";
  if (step === "complete") return "РќР°СЃС‚СЂРѕР№РєР° Р·Р°РІРµСЂС€РµРЅР°";
  return "Р“РѕС‚РѕРІРѕ";
}


function configInstructionByOs(os) {
  if (os === "iphone") {
    return [
      "РќР°Р¶РјРёС‚Рµ В«РћС‚РєСЂС‹С‚СЊ РІ HappВ» РёР»Рё СЃРєРѕРїРёСЂСѓР№С‚Рµ СЃСЃС‹Р»РєСѓ РїРѕРґРїРёСЃРєРё.",
      "РРјРїРѕСЂС‚РёСЂСѓР№С‚Рµ РїРѕРґРїРёСЃРєСѓ РІ Happ.",
      "Р Р°Р·СЂРµС€РёС‚Рµ СЃРѕР·РґР°РЅРёРµ VPN-РїСЂРѕС„РёР»СЏ РЅР° iPhone.",
      "Р’РєР»СЋС‡РёС‚Рµ VPN Рё РїСЂРѕРІРµСЂСЊС‚Рµ РґРѕСЃС‚СѓРї Рє СЃРµСЂРІРёСЃР°Рј.",
    ];
  }

  if (os === "windows" || os === "android" || os === "macos" || os === "linux") {
    return [
      "РќР°Р¶РјРёС‚Рµ В«РћС‚РєСЂС‹С‚СЊ РІ ClashВ» РґР»СЏ Р°РІС‚РѕРёРјРїРѕСЂС‚Р° РїРѕРґРїРёСЃРєРё.",
      "Р•СЃР»Рё Р°РІС‚РѕРёРјРїРѕСЂС‚ РЅРµ СЃСЂР°Р±РѕС‚Р°Р», СЃРєРѕРїРёСЂСѓР№С‚Рµ СЃСЃС‹Р»РєСѓ РїРѕРґРїРёСЃРєРё РІСЂСѓС‡РЅСѓСЋ.",
      "Р’РєР»СЋС‡РёС‚Рµ TUN РІ РєР»РёРµРЅС‚Рµ Рё Р°РєС‚РёРІРёСЂСѓР№С‚Рµ РїСЂРѕС„РёР»СЊ Pineapple VPN.",
    ];
  }

  return [
    "РћС‚РєСЂРѕР№С‚Рµ РїСЂРёР»РѕР¶РµРЅРёРµ РґР»СЏ РїРѕРґРєР»СЋС‡РµРЅРёСЏ.",
    "Р”РѕР±Р°РІСЊС‚Рµ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ РїРѕ СЃСЃС‹Р»РєРµ РёР»Рё РёР· Р±СѓС„РµСЂР° РѕР±РјРµРЅР°.",
    "РћР±РЅРѕРІРёС‚Рµ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ Рё РІРєР»СЋС‡РёС‚Рµ РїРѕРґРєР»СЋС‡РµРЅРёРµ.",
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
  const [instructionImages, setInstructionImages] = useState([]);
  const [instructionViewerIndex, setInstructionViewerIndex] = useState(null);
  const [copyNotice, setCopyNotice] = useState("");
  const [showIntro, setShowIntro] = useState(false);
  const [introSlide, setIntroSlide] = useState(0);
  const [introTouchStartX, setIntroTouchStartX] = useState(null);
  const [consentChecked, setConsentChecked] = useState(false);

  const [topupAmount, setTopupAmount] = useState(100);
  const [topupRedirecting, setTopupRedirecting] = useState(false);
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
  const topupIdFromUrl = useMemo(() => getTopupIdFromUrl(), []);
  const inTelegram = Boolean(tg?.initData);
  const botChatUrl = `https://t.me/${BOT_USERNAME}`;
  const telegramOpenUrl = topupIdFromUrl
    ? `tg://resolve?domain=${BOT_USERNAME}&startapp=topup_${topupIdFromUrl}`
    : `tg://resolve?domain=${BOT_USERNAME}`;

  const request = async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, options);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      if (res.status === 401) {
        localStorage.removeItem("token");
        setToken(null);
        throw new Error("РЎРµСЃСЃРёСЏ РёСЃС‚РµРєР»Р°. Р’С‹РїРѕР»РЅСЏСЋ РїРѕРІС‚РѕСЂРЅСѓСЋ Р°РІС‚РѕСЂРёР·Р°С†РёСЋ...");
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

    const fatal = results.find((item) => item.status === "rejected" && !String(item.reason?.message || "").includes("РЎРµСЃСЃРёСЏ РёСЃС‚РµРєР»Р°"));
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
        if (topupIdFromUrl) {
          setIsHydrating(false);
          return;
        }
        setAuthError("РћС‚РєСЂРѕР№С‚Рµ РїСЂРёР»РѕР¶РµРЅРёРµ С‡РµСЂРµР· РєРЅРѕРїРєСѓ РІ Telegram-Р±РѕС‚Рµ.");
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
  }, [tg, token, startParam, topupIdFromUrl]);

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
    let cancelled = false;

    const loadImages = async () => {
      if (!showOnboarding || onboarding?.step !== "get_config") {
        setInstructionImages([]);
        setInstructionViewerIndex(null);
        return;
      }

      const images = await loadInstructionImages(selectedOs);
      if (!cancelled) {
        setInstructionImages(images);
        setInstructionViewerIndex(null);
      }
    };

    loadImages();

    return () => {
      cancelled = true;
    };
  }, [showOnboarding, onboarding?.step, selectedOs]);

  useEffect(() => {
    if (instructionViewerIndex === null) return;

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        setInstructionViewerIndex(null);
      }
      if (event.key === "ArrowLeft") {
        setInstructionViewerIndex((prev) => {
          if (prev === null) return null;
          return Math.max(0, prev - 1);
        });
      }
      if (event.key === "ArrowRight") {
        setInstructionViewerIndex((prev) => {
          if (prev === null) return null;
          return Math.min(instructionImages.length - 1, prev + 1);
        });
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [instructionViewerIndex, instructionImages.length]);

  useEffect(() => {
    if (tab !== "setup") return;
    if (!token) return;
    if (status?.status !== "active") return;
    if (vpnConfig?.subscription_url) return;
    loadVpnConfig().catch(() => {});
  }, [tab, token, status, vpnConfig]);

  const copy = async (text, notice = "РЎСЃС‹Р»РєР° СЃРєРѕРїРёСЂРѕРІР°РЅР°") => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopyNotice(notice);
    window.setTimeout(() => setCopyNotice(""), 2000);
  };

  const shareInvite = async () => {
    const link = referralLink;
    if (!link) {
      setAuthError("Р РµС„РµСЂР°Р»СЊРЅР°СЏ СЃСЃС‹Р»РєР° РїРѕРєР° РЅРµ Р·Р°РіСЂСѓР¶РµРЅР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ С‡РµСЂРµР· РїР°СЂСѓ СЃРµРєСѓРЅРґ.");
      return;
    }

    const shareBody = [
      "рџЌЌ Pineapple VPN",
      "",
      "РќР°РґРµР¶РЅС‹Р№ РґРѕСЃС‚СѓРї Рє СЂРѕСЃСЃРёР№СЃРєРёРј СЃРµСЂРІРёСЃР°Рј РёР·-Р·Р° РіСЂР°РЅРёС†С‹: Р±Р°РЅРєРё, Р“РѕСЃСѓСЃР»СѓРіРё, Р–РљРҐ Рё СЂР°Р±РѕС‡РёРµ СЃРёСЃС‚РµРјС‹.",
      "",
      "рџЋЃ РџРѕ РјРѕРµРјСѓ РїСЂРёРіР»Р°С€РµРЅРёСЋ С‚РµР±Рµ РґРѕСЃС‚СѓРїРЅРѕ 7 РґРЅРµР№ Р±РµСЃРїР»Р°С‚РЅРѕ РІРјРµСЃС‚Рѕ 3.",
      "",
      "рџ‘† РЎСЃС‹Р»РєР° РґР»СЏ Р·Р°РїСѓСЃРєР° Р±РѕС‚Р° вЂ” РІРІРµСЂС…Сѓ СЃРѕРѕР±С‰РµРЅРёСЏ.",
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

      await copy(`${shareText}\n\n${link}`, "РџСЂРёРіР»Р°С€РµРЅРёРµ СЃРєРѕРїРёСЂРѕРІР°РЅРѕ");
      setAuthError("Р’ РІР°С€РµРј Telegram РЅРµРґРѕСЃС‚СѓРїРЅР° РїРµСЂРµСЃС‹Р»РєР°, С‚РµРєСЃС‚ СЃРєРѕРїРёСЂРѕРІР°РЅ.");
    } catch (e) {
      setAuthError(String(e?.message || "РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РєСЂС‹С‚СЊ РїРµСЂРµСЃС‹Р»РєСѓ РІ Telegram"));
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
    if (!res.ok) throw new Error("РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РєСЂС‹С‚СЊ РґРѕРєСѓРјРµРЅС‚");

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
    if (normalized && !isValidEmail(normalized)) {
      setAuthError("РЈРєР°Р¶РёС‚Рµ РєРѕСЂСЂРµРєС‚РЅС‹Р№ email РІ С„РѕСЂРјР°С‚Рµ name@example.com.");
      return;
    }

    setReceiptEmailSaving(true);
    try {
      const data = await request("/users/receipt-email", {
        method: "PUT",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalized || null }),
      });

      const savedEmail = String(data?.email || "").trim().toLowerCase();
      setReceiptEmail(savedEmail);
      setReceiptEmailDraft(savedEmail);
      setOverview((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          user: {
            ...(prev.user || {}),
            receipt_email: savedEmail || null,
          },
        };
      });
      setCopyNotice(savedEmail ? "Email РґР»СЏ С‡РµРєРѕРІ СЃРѕС…СЂР°РЅРµРЅ" : "Email РґР»СЏ С‡РµРєРѕРІ СѓРґР°Р»РµРЅ");
      window.setTimeout(() => setCopyNotice(""), 2000);
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setReceiptEmailSaving(false);
    }
  };

  const topup = async () => {
    const normalizedAmount = String(topupAmount ?? "").replace(/\D+/g, "");
    const amountRub = Number(normalizedAmount);
    if (!Number.isFinite(amountRub) || amountRub < 50) {
      setAuthError("РЈРєР°Р¶РёС‚Рµ СЃСѓРјРјСѓ РїРѕРїРѕР»РЅРµРЅРёСЏ РЅРµ РјРµРЅРµРµ 50 в‚Ѕ.");
      return;
    }

    setTopupRedirecting(true);
    setLoading(true);
    try {
      const data = await request("/payments/topup", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ amount_rub: amountRub }),
      });
      if (data.confirmation_url) {
        let opened = false;

        try {
          if (tg?.openLink) {
            tg.openLink(data.confirmation_url, {
              try_instant_view: false,
              try_browser: "external",
            });
            opened = true;
          }
        } catch {
          opened = false;
        }

        if (!opened) {
          const popup = window.open(data.confirmation_url, "_blank", "noopener,noreferrer");
          if (!popup) {
            window.location.href = data.confirmation_url;
          }
        }
        return;
      }
      throw new Error("РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РєСЂС‹С‚СЊ СЃС‚СЂР°РЅРёС†Сѓ РѕРїР»Р°С‚С‹. РџРѕРїСЂРѕР±СѓР№С‚Рµ СЃРЅРѕРІР°.");
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setLoading(false);
      setTopupRedirecting(false);
    }
  };

  const buyPlan = async (plan) => {
    const selectedPlan = plans.find((item) => item.code === plan);
    const planName = planRu(plan);
    const planDays = Number(selectedPlan?.duration_days || 0);
    const planPrice = selectedPlan?.price_rub;
    const activeUntil = status?.status === "active" ? status?.ends_at : null;

    if (planDays > 0) {
      if (activeUntil) {
        const extendedUntil = addDays(activeUntil, planDays);
        const confirmedRenew = window.confirm(
          [
            `РЈ РІР°СЃ СѓР¶Рµ РµСЃС‚СЊ Р°РєС‚РёРІРЅР°СЏ РїРѕРґРїРёСЃРєР° РґРѕ ${formatDate(activeUntil)}.`,
            "",
            `РўР°СЂРёС„ В«${planName}В» РїСЂРѕРґР»РёС‚ РґРѕСЃС‚СѓРї СЃ РґР°С‚С‹ РѕРєРѕРЅС‡Р°РЅРёСЏ С‚РµРєСѓС‰РµР№ РїРѕРґРїРёСЃРєРё.`,
            `РќРѕРІР°СЏ РґР°С‚Р° РѕРєРѕРЅС‡Р°РЅРёСЏ: ${formatDate(extendedUntil)}.`,
            "",
            "РџРѕРґС‚РІРµСЂР¶РґР°РµС‚Рµ РїСЂРѕРґР»РµРЅРёРµ?",
          ].join("\n"),
        );
        if (!confirmedRenew) return;
      } else {
        const newEndsAt = addDays(new Date(), planDays);
        const confirmedPurchase = window.confirm(
          [
            `РћС„РѕСЂРјР»РµРЅРёРµ С‚Р°СЂРёС„Р° В«${planName}В»${planPrice != null ? ` Р·Р° ${planPrice} в‚Ѕ` : ""}.`,
            `Р”Р°С‚Р° РѕРєРѕРЅС‡Р°РЅРёСЏ РїРѕСЃР»Рµ РїРѕРєСѓРїРєРё: ${formatDate(newEndsAt)}.`,
            "",
            "РџРѕРґС‚РІРµСЂР¶РґР°РµС‚Рµ РѕС„РѕСЂРјР»РµРЅРёРµ РїРѕРґРїРёСЃРєРё?",
          ].join("\n"),
        );
        if (!confirmedPurchase) return;
      }
    }

    setLoading(true);
    try {
      const purchase = await request("/subscriptions/purchase", {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });

      if (purchase?.subscription_url) {
        setVpnConfig({ subscription_url: purchase.subscription_url });
      }

      await loadAll();

      if (purchase?.is_renewal) {
        setCopyNotice("РџРѕРґРїРёСЃРєР° РїСЂРѕРґР»РµРЅР°. РљР»СЋС‡ Р°РєС‚РёРІРµРЅ. Р•СЃР»Рё РЅСѓР¶РЅРѕ РїРѕРґРєР»СЋС‡РёС‚СЊ РЅРѕРІРѕРµ СѓСЃС‚СЂРѕР№СЃС‚РІРѕ, РѕС‚РєСЂРѕР№С‚Рµ РІРєР»Р°РґРєСѓ В«РќР°СЃС‚СЂРѕР№РєР°В».");
        window.setTimeout(() => setCopyNotice(""), 3000);
        return;
      }

      try {
        await request("/onboarding/restart-device-flow", { method: "POST", headers: authHeaders });
        await refreshOnboardingState();
        setShowOnboarding(true);
        setTab("setup");
      } catch {
        setTab("setup");
      }

      setCopyNotice("РџРѕРґРїРёСЃРєР° Р°РєС‚РёРІРёСЂРѕРІР°РЅР°. Р—Р°РїСѓС‰РµРЅ РјР°СЃС‚РµСЂ РїРѕРґРєР»СЋС‡РµРЅРёСЏ РЅРѕРІРѕРіРѕ СѓСЃС‚СЂРѕР№СЃС‚РІР°.");
      window.setTimeout(() => setCopyNotice(""), 3000);
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
      setAuthError("РџРѕРІС‚РѕСЂРЅР°СЏ РЅР°СЃС‚СЂРѕР№РєР° РґРѕСЃС‚СѓРїРЅР° С‚РѕР»СЊРєРѕ РїСЂРё Р°РєС‚РёРІРЅРѕРј С‚Р°СЂРёС„Рµ РёР»Рё РїСЂРѕР±РЅРѕРј РїРµСЂРёРѕРґРµ.");
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
      setAuthError("РџРѕРґС‚РІРµСЂРґРёС‚Рµ СЃРѕРіР»Р°СЃРёРµ СЃ РїСЂР°РІРёР»Р°РјРё, С‡С‚РѕР±С‹ РїСЂРѕРґРѕР»Р¶РёС‚СЊ.");
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
      setAuthError("Р”Р»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РєРѕРЅС„РёРіСѓСЂР°С†РёРё РЅСѓР¶РµРЅ Р°РєС‚РёРІРЅС‹Р№ С‚Р°СЂРёС„ РёР»Рё РїСЂРѕР±РЅС‹Р№ РїРµСЂРёРѕРґ.");
      return;
    }

    setConfigGenerating(true);
    setLoading(true);
    try {
      const config = await request("/onboarding/config", { method: "POST", headers: authHeaders });
      setOnboardingConfig(config);
      setSelectedOs(config.platform || selectedOs);
      setVpnConfig(config);
      await refreshOnboardingState();
      await loadAll();
    } catch (e) {
      setAuthError(String(e.message));
    } finally {
      setConfigGenerating(false);
      setLoading(false);
    }
  };

  const openInstallUrl = (url) => {
    if (!url) return;
    if (tg?.openLink) {
      tg.openLink(url);
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
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
  const normalizedReceiptEmailDraft = String(receiptEmailDraft || "").trim().toLowerCase();
  const normalizedReceiptEmail = String(receiptEmail || "").trim().toLowerCase();
  const isReceiptEmailDraftValid = !normalizedReceiptEmailDraft || isValidEmail(normalizedReceiptEmailDraft);
  const canSaveReceiptEmail = normalizedReceiptEmailDraft !== normalizedReceiptEmail && isReceiptEmailDraftValid;

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
    onboardingConfig?.subscription_url
      || vpnConfig?.subscription_url
      || (selectedOs === "iphone" ? (vpnConfig?.subscription_url_happ || vpnConfig?.subscription_url_hiddify) : vpnConfig?.subscription_url_clash),
  );
  const setupInstallUrl = onboardingConfig?.install_url || vpnConfig?.install_urls?.[selectedOs] || "";
  const setupInstallCta =
    selectedOs === "iphone"
      ? "РћС‚РєСЂС‹С‚СЊ РІ Happ"
      : "РћС‚РєСЂС‹С‚СЊ РІ Clash";
  const configHelp = configInstructionByOs(selectedOs);

  const currentInstructionImage =
    instructionViewerIndex === null ? "" : instructionImages[instructionViewerIndex] || "";

  const openInstructionViewer = (index) => {
    setInstructionViewerIndex(index);
  };

  const closeInstructionViewer = () => {
    setInstructionViewerIndex(null);
  };

  const showPrevInstructionImage = () => {
    setInstructionViewerIndex((prev) => {
      if (prev === null) return null;
      return Math.max(0, prev - 1);
    });
  };

  const showNextInstructionImage = () => {
    setInstructionViewerIndex((prev) => {
      if (prev === null) return null;
      return Math.min(instructionImages.length - 1, prev + 1);
    });
  };

  const supportUsername = parseSupportUsername(SUPPORT_URL);
  const latestSubscriptionPayment = [...payments]
    .filter((item) => item?.kind === "subscription_debit" && item?.status === "paid")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
  const supportSubscriptionStartedAt =
    status?.plan === "trial"
      ? overview?.trial?.activated_at || null
      : latestSubscriptionPayment?.created_at || null;
  const supportMessage = [
    "Р—РґСЂР°РІСЃС‚РІСѓР№С‚Рµ! РќСѓР¶РЅР° РїРѕРјРѕС‰СЊ СЃ Pineapple VPN.",
    "",
    "Р”Р°РЅРЅС‹Рµ РґР»СЏ Р±С‹СЃС‚СЂРѕР№ РґРёР°РіРЅРѕСЃС‚РёРєРё:",
    `Telegram ID: ${overview?.user?.telegram_id || tg?.initDataUnsafe?.user?.id || "РЅРµ РЅР°Р№РґРµРЅ"}`,
    `Username: @${overview?.user?.username || tg?.initDataUnsafe?.user?.username || "РЅРµ СѓРєР°Р·Р°РЅ"}`,
    `РЎС‚Р°С‚СѓСЃ РїРѕРґРїРёСЃРєРё: ${statusRu(status?.status)}`,
    `РўР°СЂРёС„: ${planRu(status?.plan)}`,
    `РћС„РѕСЂРјР»РµРЅР°: ${formatDate(supportSubscriptionStartedAt)}`,
    `РСЃС‚РµРєР°РµС‚: ${formatDate(status?.ends_at || overview?.subscription?.ends_at)}`,
    `РљР»СЋС‡ VPN: ${setupSubscriptionUrl || "РµС‰Рµ РЅРµ РїРѕР»СѓС‡РµРЅ"}`,
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
            setCopyNotice("РџРѕРїРѕР»РЅРµРЅРёРµ РєРѕС€РµР»СЊРєР° РїРѕРґС‚РІРµСЂР¶РґРµРЅРѕ");
            await loadAll();
          }
          return;
        }

        if (st === "canceled" || st === "failed") {
          if (!cancelled) {
            clearTopupIdFromUrl();
            setAuthError(st === "canceled" ? "РџР»Р°С‚РµР¶ Р±С‹Р» РѕС‚РјРµРЅРµРЅ." : "РџР»Р°С‚РµР¶ РЅРµ Р·Р°РІРµСЂС€РµРЅ. РџРѕРїСЂРѕР±СѓР№С‚Рµ СЃРЅРѕРІР°.");
          }
          return;
        }

        if (!cancelled) {
          if (attempts === 0) {
            setAuthError("РџР»Р°С‚РµР¶ РѕР±СЂР°Р±Р°С‚С‹РІР°РµС‚СЃСЏ. РћР±С‹С‡РЅРѕ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ Р·Р°РЅРёРјР°РµС‚ РЅРµСЃРєРѕР»СЊРєРѕ СЃРµРєСѓРЅРґ.");
          }
          if (attempts < 20) {
            attempts += 1;
            timer = window.setTimeout(poll, 3000);
          } else {
            clearTopupIdFromUrl();
            setAuthError("РџР»Р°С‚РµР¶ РµС‰Рµ РѕР±СЂР°Р±Р°С‚С‹РІР°РµС‚СЃСЏ. РћР±РЅРѕРІРёС‚Рµ СЌРєСЂР°РЅ С‡РµСЂРµР· РјРёРЅСѓС‚Сѓ.");
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

  if (!inTelegram && topupIdFromUrl) {
    return (
      <div className="app-shell">
        <div className="bg-orb bg-orb-a" />
        <div className="bg-orb bg-orb-b" />
        <main className="app-main">
          <section className="onboarding-shell pulse-in">
            <article className="card browser-return-card">
              <h3>РћРїР»Р°С‚Р° РѕС‚РєСЂС‹С‚Р° РІ Р±СЂР°СѓР·РµСЂРµ</h3>
              <p>Р§С‚РѕР±С‹ СѓРІРёРґРµС‚СЊ СЂРµР·СѓР»СЊС‚Р°С‚ РїРѕРїРѕР»РЅРµРЅРёСЏ, РІРµСЂРЅРёС‚РµСЃСЊ РІ Telegram Рё СЃРЅРѕРІР° РѕС‚РєСЂРѕР№С‚Рµ Pineapple VPN.</p>
              <div className="browser-return-actions">
                <a className="soft-link" href={telegramOpenUrl}>РћС‚РєСЂС‹С‚СЊ Telegram</a>
                <a className="soft-link" href={botChatUrl} target="_blank" rel="noreferrer">РћС‚РєСЂС‹С‚СЊ Р±РѕС‚Р°</a>
                <button className="soft-btn" onClick={() => copy(botChatUrl, "РЎСЃС‹Р»РєР° РЅР° Р±РѕС‚Р° СЃРєРѕРїРёСЂРѕРІР°РЅР°")}>РЎРєРѕРїРёСЂРѕРІР°С‚СЊ СЃСЃС‹Р»РєСѓ РЅР° Р±РѕС‚Р°</button>
              </div>
              <small className="muted">Р•СЃР»Рё Р°РІС‚РѕРїРµСЂРµС…РѕРґ РЅРµ СЃСЂР°Р±РѕС‚Р°Р», РѕС‚РєСЂРѕР№С‚Рµ Р±РѕС‚Р° РІСЂСѓС‡РЅСѓСЋ Рё РЅР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ Р·Р°РїСѓСЃРєР° MiniApp.</small>
            </article>
          </section>
        </main>
      </div>
    );
  }

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
                <h3>Р—Р°РіСЂСѓР¶Р°РµРј РІР°С€ РєР°Р±РёРЅРµС‚</h3>
                <p>РџСЂРѕРІРµСЂСЏРµРј Р°РІС‚РѕСЂРёР·Р°С†РёСЋ Рё РІРѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµРј С€Р°Рі РЅР°СЃС‚СЂРѕР№РєРё</p>
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
                  <span>Р—Р°С‰РёС‰РµРЅРЅС‹Р№ РґРѕСЃС‚СѓРї Рє РІР°Р¶РЅС‹Рј СЃРµСЂРІРёСЃР°Рј РёР· Р»СЋР±РѕР№ С‚РѕС‡РєРё РјРёСЂР°</span>
                </div>
              </div>
              <div className="intro-carousel">
                <button className="intro-arrow left" onClick={introPrev} aria-label="РџСЂРµРґС‹РґСѓС‰РёР№ СЃР»Р°Р№Рґ">
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
                <button className="intro-arrow right" onClick={introNext} aria-label="РЎР»РµРґСѓСЋС‰РёР№ СЃР»Р°Р№Рґ">
                  <svg viewBox="0 0 24 24"><path d="m9 5 7 7-7 7" /></svg>
                </button>
              </div>
              <div className="intro-dots">
                {INTRO_SLIDES.map((_, idx) => (
                  <button key={idx} className={`dot ${introSlide === idx ? "active" : ""}`} onClick={() => setIntroSlide(idx)} aria-label={`РЎР»Р°Р№Рґ ${idx + 1}`} />
                ))}
              </div>
              <div className="intro-cards-grid">
                <div className="intro-chip-card trial-highlight">
                  <h4>{"РџСЂРѕР±РЅС‹Р№ РїРµСЂРёРѕРґ"}</h4>
                  <div className="value">{trialDays} {"РґРЅ."}</div>
                  <small>{trialDays > 3 ? "РџРѕ СЂРµС„РµСЂР°Р»СЊРЅРѕР№ СЃСЃС‹Р»РєРµ" : "РЎС‚Р°РЅРґР°СЂС‚РЅС‹Р№ РґРѕСЃС‚СѓРї"}</small>
                </div>
                <div className="intro-chip-card">
                  <h4>{"РўР°СЂРёС„С‹"}</h4>
                  <div className="tariff-line"><span>{"РќРµРґРµР»СЏ"}</span><strong>{weekPlanPrice != null ? `${weekPlanPrice} в‚Ѕ` : "вЂ”"}</strong></div>
                  <div className="tariff-line"><span>{"РњРµСЃСЏС†"}</span><strong>{monthPlanPrice != null ? `${monthPlanPrice} в‚Ѕ` : "вЂ”"}</strong></div>
                </div>
                <div className="intro-chip-card">
                  <h4>{"РЎРїРѕСЃРѕР±С‹ РѕРїР»Р°С‚С‹"}</h4>
                  <div className="pay-icons"><span>{"РЎР‘Рџ"}</span><span>{"РљР°СЂС‚Р°"}</span><span>SberPay</span></div>
                </div>
              </div>
              <button className="cta-main" onClick={startIntroFlow}>{"РќР°С‡Р°С‚СЊ РїСЂРѕР±РЅС‹Р№ РїРµСЂРёРѕРґ"}</button>
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
                  aria-label="РЎРІРµСЂРЅСѓС‚СЊ РјР°СЃС‚РµСЂ"
                  title="РЎРІРµСЂРЅСѓС‚СЊ РјР°СЃС‚РµСЂ"
                >
                  Г—
                </button>
              )}
              <div className="onboarding-progress-wrap">
                <div className="onboarding-progress-meta">РЁР°Рі {progressStepIndex} РёР· {progressTotal}</div>
                <div className="onboarding-progress">
                  <span style={{ width: `${Math.round((progressStepIndex / progressTotal) * 100)}%` }} />
                </div>
              </div>

              <h2>{onboardingTitle(onboardingStep)}</h2>

              {onboardingStep === "welcome" && (
                <>
                  <p>
                    Pineapple VPN РїРѕРјРѕРіР°РµС‚ Р±РµР·РѕРїР°СЃРЅРѕ РїРѕР»СЊР·РѕРІР°С‚СЊСЃСЏ СЂРѕСЃСЃРёР№СЃРєРёРјРё СЃРµСЂРІРёСЃР°РјРё РёР·-Р·Р° РіСЂР°РЅРёС†С‹:
                    Р±Р°РЅРєРё, Р“РѕСЃСѓСЃР»СѓРіРё, Р–РљРҐ, СЂР°Р±РѕС‡РёРµ Рё РєРѕСЂРїРѕСЂР°С‚РёРІРЅС‹Рµ СЃРёСЃС‚РµРјС‹.
                  </p>
                  <p className="muted">РЎРµСЂРІРёСЃ РЅРµ РїСЂРµРґРЅР°Р·РЅР°С‡РµРЅ РґР»СЏ РѕР±С…РѕРґР° Р±Р»РѕРєРёСЂРѕРІРѕРє Рё РЅРµР·Р°РєРѕРЅРЅРѕР№ РґРµСЏС‚РµР»СЊРЅРѕСЃС‚Рё.</p>

                  <div className="doc-links inline-links onboarding-links">
                    <button className="link-btn" onClick={() => openDoc("public-offer", "РџСѓР±Р»РёС‡РЅР°СЏ РѕС„РµСЂС‚Р°")}>РЎРѕРіР»Р°С€РµРЅРёРµ</button>
                    <button className="link-btn" onClick={() => openDoc("privacy-policy", "РџРѕР»РёС‚РёРєР° РєРѕРЅС„РёРґРµРЅС†РёР°Р»СЊРЅРѕСЃС‚Рё")}>РџРѕР»РёС‚РёРєР°</button>
                    <button className="link-btn" onClick={() => openDoc("acceptable-use", "РџСЂР°РІРёР»Р° РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ")}>РџСЂР°РІРёР»Р°</button>
                  </div>

                  <label className="consent-line">
                    <input type="checkbox" checked={consentChecked} onChange={(e) => setConsentChecked(e.target.checked)} />
                    <span>РЇ РѕР·РЅР°РєРѕРјРёР»СЃСЏ Рё РїСЂРёРЅРёРјР°СЋ РїСЂР°РІРёР»Р° СЃРµСЂРІРёСЃР°</span>
                  </label>

                  <button disabled={loading} onClick={onboardingAcceptTerms}>РџСЂРѕРґРѕР»Р¶РёС‚СЊ</button>
                </>
              )}

              {onboardingStep === "trial_offer" && (
                <>
                  <p>
                    Р’Р°Рј РґРѕСЃС‚СѓРїРµРЅ РїСЂРѕР±РЅС‹Р№ РїРµСЂРёРѕРґ <strong>{onboarding?.trial_days || 3} РґРЅСЏ</strong>
                    {(onboarding?.trial_days || 3) > 3 ? " РїРѕ СЂРµС„РµСЂР°Р»СЊРЅРѕР№ СЃСЃС‹Р»РєРµ" : ""}.
                  </p>
                  <p className="muted">РџРѕР»РЅС‹Р№ РґРѕСЃС‚СѓРї Рє РїРѕРґРєР»СЋС‡РµРЅРёСЋ, С‡С‚РѕР±С‹ РїСЂРѕРІРµСЂРёС‚СЊ СЂР°Р±РѕС‚Сѓ СЃРµСЂРІРёСЃР° РїРµСЂРµРґ РѕРїР»Р°С‚РѕР№.</p>
                  <button disabled={loading} onClick={onboardingActivateTrial}>РџРѕРїСЂРѕР±РѕРІР°С‚СЊ Р±РµСЃРїР»Р°С‚РЅРѕ</button>
                </>
              )}

              {onboardingStep === "device_select" && (
                <>
                  {isRepeatDeviceFlow && (
                    <p className="muted">Р’Р°С€ РєР»СЋС‡ СѓР¶Рµ СЃРѕР·РґР°РЅ Рё Р°РєС‚РёРІРµРЅ. РЎРµР№С‡Р°СЃ РЅР°СЃС‚СЂРѕРёРј РµРіРѕ РґР»СЏ РЅРѕРІРѕРіРѕ СѓСЃС‚СЂРѕР№СЃС‚РІР°.</p>
                  )}
                  <p>Р’С‹Р±РµСЂРёС‚Рµ СѓСЃС‚СЂРѕР№СЃС‚РІРѕ, РЅР° РєРѕС‚РѕСЂРѕРј С…РѕС‚РёС‚Рµ РЅР°СЃС‚СЂРѕРёС‚СЊ РїРѕРґРєР»СЋС‡РµРЅРёРµ РІ РїРµСЂРІСѓСЋ РѕС‡РµСЂРµРґСЊ.</p>
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
                  <button disabled={loading} onClick={onboardingSelectDevice}>РџСЂРѕРґРѕР»Р¶РёС‚СЊ</button>
                </>
              )}

              {onboardingStep === "install_app" && (
                <>
                  <p>
                    РЈСЃС‚Р°РЅРѕРІРёС‚Рµ РїСЂРёР»РѕР¶РµРЅРёРµ <strong>{onboardingInstruction?.app_name || "РґР»СЏ РІС‹Р±СЂР°РЅРЅРѕР№ РћРЎ"}</strong>.
                    РџРѕСЃР»Рµ СѓСЃС‚Р°РЅРѕРІРєРё РІРµСЂРЅРёС‚РµСЃСЊ Рё РїРѕРґС‚РІРµСЂРґРёС‚Рµ.
                  </p>
                  {onboardingInstruction?.download_url && (
                    <a className="download-link" href={onboardingInstruction.download_url} target="_blank" rel="noreferrer">
                      РЎРєР°С‡Р°С‚СЊ РїСЂРёР»РѕР¶РµРЅРёРµ
                    </a>
                  )}
                  <ol className="steps clean">
                    {(onboardingInstruction?.steps || []).map((line, idx) => (
                      <li key={idx} className="pending">{line}</li>
                    ))}
                  </ol>
                  <button disabled={loading} onClick={onboardingConfirmInstall}>РЇ СѓСЃС‚Р°РЅРѕРІРёР» РїСЂРёР»РѕР¶РµРЅРёРµ</button>
                </>
              )}

              {onboardingStep === "get_config" && (
                <>
                  {configGenerating && (
                    <div className="config-loader-screen">
                      <div className="loader-spinner" />
                      <h3>{"Р“РѕС‚РѕРІРёРј РІР°С€Сѓ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ VPN"}</h3>
                      <p>{"Р­С‚Рѕ РјРѕР¶РµС‚ Р·Р°РЅСЏС‚СЊ РЅРµСЃРєРѕР»СЊРєРѕ СЃРµРєСѓРЅРґ"}</p>
                    </div>
                  )}

                  {!configGenerating && !setupSubscriptionUrl && (
                    <>
                      <p>{"РћСЃС‚Р°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РїРµСЂСЃРѕРЅР°Р»СЊРЅСѓСЋ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ Рё РґРѕР±Р°РІРёС‚СЊ РµРµ РІ РїСЂРёР»РѕР¶РµРЅРёРµ."}</p>
                      <button disabled={loading} onClick={onboardingGetConfig}>{"РџРѕР»СѓС‡РёС‚СЊ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ"}</button>
                    </>
                  )}

                  {!configGenerating && !!setupSubscriptionUrl && (
                    <div className="vpn-ready-layout">
                      <h3>{"Р’Р°С€ VPN РіРѕС‚РѕРІ"}</h3>
                      <p className="muted">{onboardingConfig?.message || "РћСЃС‚Р°Р»РѕСЃСЊ РґРѕР±Р°РІРёС‚СЊ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ РІ РїСЂРёР»РѕР¶РµРЅРёРµ"}</p>

                      <div className="config-box">
                        {!!setupInstallUrl && (
                          <div className="row wrap-row">
                            <button onClick={() => openInstallUrl(setupInstallUrl)}>{setupInstallCta}</button>
                            <button className="soft-btn" onClick={() => setShowQr((v) => !v)}>{showQr ? "РЎРєСЂС‹С‚СЊ QR РєРѕРґ" : "РџРѕРєР°Р·Р°С‚СЊ QR РєРѕРґ"}</button>
                          </div>
                        )}
                        <div className="config-item">
                          <label>{"РЎСЃС‹Р»РєР° РїРѕРґРїРёСЃРєРё"}</label>
                          <textarea readOnly value={setupSubscriptionUrl} rows={4} />
                        </div>
                        <div className="row wrap-row">
                          <button onClick={() => copy(setupSubscriptionUrl)}>{"РЎРєРѕРїРёСЂРѕРІР°С‚СЊ СЃСЃС‹Р»РєСѓ"}</button>
                        </div>
                        {showQr && (
                          <div className="qr-wrap">
                            <QRCodeSVG value={setupSubscriptionUrl} size={210} level="M" includeMargin />
                          </div>
                        )}
                      </div>

                      <article className="mini-instruction">
                        <h4>{"РљР°Рє РїРѕРґРєР»СЋС‡РёС‚СЊ VPN"}</h4>
                        <ol className="steps clean">
                          {configHelp.map((line, idx) => (
                            <li key={idx} className="pending">{line}</li>
                          ))}
                        </ol>
                      </article>

                      {instructionImages.length > 0 && (
                        <section className="instruction-screens-block">
                          <h4>{"РЎРєСЂРёРЅС€РѕС‚С‹ РЅР°СЃС‚СЂРѕР№РєРё"}</h4>
                          <p className="muted">{"РќР°Р¶РјРёС‚Рµ РЅР° СЃРєСЂРёРЅС€РѕС‚, С‡С‚РѕР±С‹ РѕС‚РєСЂС‹С‚СЊ РµРіРѕ РІ РїРѕР»РЅРѕРј СЂР°Р·РјРµСЂРµ."}</p>
                          <div className="instruction-thumbs" role="list">
                            {instructionImages.map((src, idx) => (
                              <button
                                key={`${src}-${idx}`}
                                type="button"
                                className="instruction-thumb"
                                onClick={() => openInstructionViewer(idx)}
                                aria-label={`РЎРєСЂРёРЅС€РѕС‚ ${idx + 1}`}
                              >
                                <img src={src} alt={`Step ${idx + 1}`} loading="lazy" />
                              </button>
                            ))}
                          </div>
                        </section>
                      )}

                      <button onClick={onboardingComplete} disabled={loading}>{"РЇ РґРѕР±Р°РІРёР» РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ"}</button>

                      <div className="help-box">
                        <strong>{"РќРµ РїРѕР»СѓС‡Р°РµС‚СЃСЏ РїРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ?"}</strong>
                        <div className="row wrap-row">
                          <a className="soft-link" href={SUPPORT_URL} target="_blank" rel="noreferrer">{"РќР°РїРёСЃР°С‚СЊ РІ РїРѕРґРґРµСЂР¶РєСѓ"}</a>
                        </div>
                      </div>

                      {instructionViewerIndex !== null && currentInstructionImage && (
                        <div className="instruction-viewer-overlay" onClick={closeInstructionViewer}>
                          <div className="instruction-viewer" onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              className="instruction-viewer-close"
                              onClick={closeInstructionViewer}
                              aria-label={"Р—Р°РєСЂС‹С‚СЊ"}
                            >
                              Г—
                            </button>
                            <img src={currentInstructionImage} alt={`Step ${instructionViewerIndex + 1}`} />
                            <div className="instruction-viewer-footer">
                              <button
                                type="button"
                                className="soft-btn"
                                onClick={showPrevInstructionImage}
                                disabled={instructionViewerIndex <= 0}
                              >
                                РќР°Р·Р°Рґ
                              </button>
                              <span>{instructionViewerIndex + 1} / {instructionImages.length}</span>
                              <button
                                type="button"
                                className="soft-btn"
                                onClick={showNextInstructionImage}
                                disabled={instructionViewerIndex >= instructionImages.length - 1}
                              >
                                Р’РїРµСЂРµРґ
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {(onboardingStep === "complete" || onboardingStep === "done") && (
                <>
                  <p>VPN РіРѕС‚РѕРІ Рє РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЋ. Р’С‹ РјРѕР¶РµС‚Рµ РѕС‚РєСЂС‹С‚СЊ РЅР°СЃС‚СЂРѕР№РєРё, РґРѕРєСѓРјРµРЅС‚Р°С†РёСЋ РёР»Рё РѕР±СЂР°С‚РёС‚СЊСЃСЏ РІ РїРѕРґРґРµСЂР¶РєСѓ.</p>
                  <div className="row wrap-row">
                    <button disabled={loading} onClick={onboardingComplete}>РџРµСЂРµР№С‚Рё РІ РїСЂРёР»РѕР¶РµРЅРёРµ</button>
                    <button className="soft-btn" onClick={() => { setShowOnboarding(false); setTab("setup"); }}>РћС‚РєСЂС‹С‚СЊ РЅР°СЃС‚СЂРѕР№РєРё</button>
                    <button className="soft-btn" onClick={() => setTab("help")}>Р”РѕРєСѓРјРµРЅС‚С‹</button>
                    <a className="soft-link" href={SUPPORT_URL} target="_blank" rel="noreferrer">РџРѕРґРґРµСЂР¶РєР°</a>
                  </div>
                </>
              )}
            </article>

            {!!docHtml && (
              <article ref={docCardRef} className="card">
                <div className="row between">
                  <h3>{docTitle}</h3>
                  <button onClick={closeDoc}>РќР°Р·Р°Рґ</button>
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
              <p>Р—Р°С‰РёС‰РµРЅРЅС‹Р№ СѓРґР°Р»РµРЅРЅС‹Р№ РґРѕСЃС‚СѓРї Рє СЂРѕСЃСЃРёР№СЃРєРёРј СЃРµСЂРІРёСЃР°Рј РёР·-Р·Р° РіСЂР°РЅРёС†С‹</p>
              <div className="hero-status-grid">
                <div className="hero-status-item">
                  <span>РЎС‚Р°С‚СѓСЃ</span>
                  <strong>{statusRu(status?.status)}</strong>
                </div>
                {hasPlanInfo && (
                  <>
                    <div className="hero-status-item">
                      <span>РўР°СЂРёС„</span>
                      <strong>{planRu(status?.plan)}</strong>
                    </div>
                    <div className="hero-status-item">
                      <span>РћРєРѕРЅС‡Р°РЅРёРµ</span>
                      <strong>{formatDate(subEndsAt)}</strong>
                    </div>
                    <div className="hero-status-item">
                      <span>РћСЃС‚Р°Р»РѕСЃСЊ</span>
                      <strong>{subDaysLeft === null ? "вЂ”" : `${subDaysLeft} РґРЅ.`}</strong>
                    </div>
                  </>
                )}
              </div>
            </div>

            <article className="card tariffs-card">
              <h3>РўР°СЂРёС„С‹</h3>
              <div className="grid two">
                {plans.map((plan) => (
                  <div className="price-card modern" key={plan.code}>
                    <div className="price-head">
                      <div className="price-name">{planRu(plan.code)}</div>
                      <div className="price-badge">{plan.duration_days} РґРЅРµР№</div>
                    </div>
                    <div className="price-value">{plan.price_rub} в‚Ѕ</div>
                    <p className="muted">РћРїР»Р°С‚Р° РёР· РєРѕС€РµР»СЊРєР°, РїСЂРѕРґР»РµРЅРёРµ Р±РµР· СЃРјРµРЅС‹ РєР»СЋС‡Р°.</p>
                    <button disabled={loading} onClick={() => buyPlan(plan.code)}>РћС„РѕСЂРјРёС‚СЊ</button>
                  </div>
                ))}
              </div>
            </article>
          </section>
        )}

        {!isHydrating && !showOnboarding && tab === "wallet" && (
          <section className="page">
            <article className="card wallet-balance">
              <h3>РљРѕС€РµР»РµРє</h3>
              <div className="balance-value">{wallet} в‚Ѕ</div>
              <small>РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РґР»СЏ РѕРїР»Р°С‚С‹ РїРѕРґРїРёСЃРѕРє</small>
            </article>

            <article className="card receipt-email-card">
              <h3>Email РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ С‡РµРєРѕРІ</h3>
              <p className="muted">Email РЅРµРѕР±СЏР·Р°С‚РµР»РµРЅ. Р•СЃР»Рё СѓРєР°Р¶РµС‚Рµ РµРіРѕ, РјС‹ СЃРјРѕР¶РµРј РѕС‚РїСЂР°РІРёС‚СЊ РєР°СЃСЃРѕРІС‹Р№ С‡РµРє РїРѕСЃР»Рµ РѕРїР»Р°С‚С‹ РІ С‚РµС‡РµРЅРёРµ 24 С‡Р°СЃРѕРІ.</p>
              <div className="row receipt-email-row">
                <input
                  type="email"
                  value={receiptEmailDraft}
                  placeholder="name@example.com"
                  onChange={(e) => setReceiptEmailDraft(e.target.value)}
                />
                <button disabled={receiptEmailSaving || !canSaveReceiptEmail} onClick={saveReceiptEmail}>
                  {receiptEmailSaving ? "РЎРѕС…СЂР°РЅСЏРµРј..." : "РЎРѕС…СЂР°РЅРёС‚СЊ"}
                </button>
              </div>
              {hasReceiptEmail ? <small>РўРµРєСѓС‰РёР№ email РґР»СЏ РѕС‚РїСЂР°РІРєРё С‡РµРєР°: {receiptEmail}</small> : <small className="muted">Email РЅРµ СѓРєР°Р·Р°РЅ. Р­С‚Рѕ РЅРµ РїРѕРјРµС€Р°РµС‚ РѕРїР»Р°С‚Рµ.</small>}
            </article>

            <article className="card">
              <h3>РџРѕРїРѕР»РЅРµРЅРёРµ РєРѕС€РµР»СЊРєР°</h3>
              <div className="row">
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  autoComplete="off"
                  value={topupAmount}
                  onChange={(e) => setTopupAmount(e.target.value.replace(/\D+/g, ""))}
                />
                <button disabled={loading || topupRedirecting} onClick={topup}>
                  {topupRedirecting ? "РџРµСЂРµС…РѕРґРёРј Рє РѕРїР»Р°С‚Рµ..." : "РџРѕРїРѕР»РЅРёС‚СЊ"}
                </button>
              </div>
              {topupRedirecting && (
                <div className="payment-loader-inline" role="status" aria-live="polite">
                  <div className="loader-spinner small" />
                  <div className="payment-loader-copy">
                    <strong>Р“РѕС‚РѕРІРёРј РїРµСЂРµС…РѕРґ РІ Р®Kassa</strong>
                    <small>РћС‚РєСЂС‹РІР°РµРј СЃС‚СЂР°РЅРёС†Сѓ РѕРїР»Р°С‚С‹, СЌС‚Рѕ РјРѕР¶РµС‚ Р·Р°РЅСЏС‚СЊ РЅРµСЃРєРѕР»СЊРєРѕ СЃРµРєСѓРЅРґ.</small>
                  </div>
                </div>
              )}
              <small>РњРёРЅРёРјР°Р»СЊРЅР°СЏ СЃСѓРјРјР° 50 в‚Ѕ</small>
                          </article>

            <article className="card">
              <h3>РСЃС‚РѕСЂРёСЏ РѕРїРµСЂР°С†РёР№</h3>
              <div className="ops-list">
                {payments.map((item) => {
                  const meta = operationMeta(item);
                  return (
                    <div key={item.id} className={`op-row ${meta.cls}`}>
                      <div>
                        <div className="op-title">{meta.title}</div>
                        <div className="op-date">{formatDate(item.created_at)}</div>
                      </div>
                      <div className="op-amount">{meta.sign}{item.amount_rub} в‚Ѕ</div>
                    </div>
                  );
                })}
                {!payments.length && <div className="empty">РћРїРµСЂР°С†РёР№ РїРѕРєР° РЅРµС‚</div>}
              </div>
            </article>
          </section>
        )}

        {!isHydrating && !showOnboarding && tab === "setup" && (
          <section className="page">
            <article className="card">
              <h3>Р’Р°С€Р° Р°РєС‚РёРІРЅР°СЏ СЃСЃС‹Р»РєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ</h3>
              <p className="muted">Р­С‚РѕС‚ РєР»СЋС‡ РјРѕР¶РЅРѕ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ РЅР° РІСЃРµС… РІР°С€РёС… СѓСЃС‚СЂРѕР№СЃС‚РІР°С….</p>
              {hasActiveAccess && !setupSubscriptionUrl && (
                <button onClick={loadVpnConfig} disabled={loading || !hasActiveAccess}>РџРѕР»СѓС‡РёС‚СЊ / РѕР±РЅРѕРІРёС‚СЊ РєР»СЋС‡</button>
              )}
              {status?.status !== "active" && <p className="muted">Р”Р»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РєР»СЋС‡Р° Р°РєС‚РёРІРёСЂСѓР№С‚Рµ РїСЂРѕР±РЅС‹Р№ РїРµСЂРёРѕРґ РёР»Рё РѕРїР»Р°С‚РёС‚Рµ С‚Р°СЂРёС„.</p>}
              {hasActiveAccess && !!setupSubscriptionUrl && (
                <div className="config-box">
                  <div className="config-item">
                    <label>РЎСЃС‹Р»РєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ</label>
                    <textarea readOnly value={setupSubscriptionUrl} rows={4} />
                  </div>
                  <button onClick={() => copy(setupSubscriptionUrl)}>РЎРєРѕРїРёСЂРѕРІР°С‚СЊ РєР»СЋС‡</button>
                </div>
              )}
            </article>

            <article className="card">
              <h3>РџРѕРґРєР»СЋС‡РёС‚СЊ РЅРѕРІРѕРµ СѓСЃС‚СЂРѕР№СЃС‚РІРѕ</h3>
              <p className="muted">РџРѕРјРѕР¶РµРј Р±С‹СЃС‚СЂРѕ РЅР°СЃС‚СЂРѕРёС‚СЊ VPN РЅР° РЅРѕРІРѕРј СѓСЃС‚СЂРѕР№СЃС‚РІРµ: РІС‹Р±РѕСЂ РћРЎ, СѓСЃС‚Р°РЅРѕРІРєР° РєР»РёРµРЅС‚Р° Рё РёРјРїРѕСЂС‚ РєРѕРЅС„РёРіСѓСЂР°С†РёРё.</p>
              <p className="muted">Р”РѕСЃС‚СѓРїРЅС‹Рµ РћРЎ: Windows, iPhone, Android, macOS, Linux.</p>
              <button disabled={loading || !hasActiveAccess} onClick={startDeviceFlow}>Р—Р°РїСѓСЃС‚РёС‚СЊ РјР°СЃС‚РµСЂ РїРѕРґРєР»СЋС‡РµРЅРёСЏ</button>
            </article>
          </section>
        )}

        {!isHydrating && !showOnboarding && tab === "referral" && (
          <section className="page">
            <article className="card">
              <h3>Р РµС„РµСЂР°Р»СЊРЅР°СЏ СЃРёСЃС‚РµРјР°</h3>
              <p className="muted">Р”СЂСѓРі РїРѕР»СѓС‡РёС‚ 7 РґРЅРµР№ Р±РµСЃРїР»Р°С‚РЅРѕ РІРјРµСЃС‚Рѕ 3, Р° РІС‹ РїРѕР»СѓС‡Р°РµС‚Рµ 10% РѕС‚ Р»СЋР±РѕРіРѕ РїРѕРїРѕР»РЅРµРЅРёСЏ РґСЂСѓРіР°, РїРѕРєР° РѕРЅ РїРѕР»СЊР·СѓРµС‚СЃСЏ VPN.</p>
              <p>РЎСЃС‹Р»РєР° РІ Telegram-Р±РѕС‚:</p>
              <div className="ref-link">{referralLink || "-"}</div>
              <div className="row">
                <button onClick={() => copy(referralLink)}>РЎРєРѕРїРёСЂРѕРІР°С‚СЊ СЃСЃС‹Р»РєСѓ</button>
              </div>
              <p>Р“РѕС‚РѕРІРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ-РїСЂРёРіР»Р°С€РµРЅРёРµ:</p>
              <div className="ref-link">{referralInviteMessage || "-"}</div>
              <div className="row ref-share-row">
                <button onClick={() => copy(referralInviteMessage, "РџСЂРёРіР»Р°С€РµРЅРёРµ СЃРєРѕРїРёСЂРѕРІР°РЅРѕ")}>РЎРєРѕРїРёСЂРѕРІР°С‚СЊ РїСЂРёРіР»Р°С€РµРЅРёРµ</button>
                <button className="soft-btn" onClick={shareInvite}>РџРѕРґРµР»РёС‚СЊСЃСЏ</button>
              </div>
              <div className="grid three">
                <div className="stat">РџСЂРёРіР»Р°С€РµРЅРѕ: {referralStats?.invited_count || 0}</div>
                <div className="stat">РќР°С‡РёСЃР»РµРЅРѕ: {referralStats?.earned_rub || 0} в‚Ѕ</div>
              </div>
            </article>

            <article className="card">
              <h3>РЎРїРёСЃРѕРє СЂРµС„РµСЂР°Р»РѕРІ</h3>
              <ul className="list">
                {referralList.map((r, i) => (
                  <li key={`${r.invitee_id}-${i}`}>@{r.username || "-"} +{r.earned_rub} в‚Ѕ</li>
                ))}
                {!referralList.length && <li>Р РµС„РµСЂР°Р»РѕРІ РїРѕРєР° РЅРµС‚</li>}
              </ul>
            </article>
          </section>
        )}

        {!isHydrating && !showOnboarding && tab === "help" && (
          <section className="page">
            {!docHtml && (
              <article className="card">
                <h3>{"Р”РѕРєСѓРјРµРЅС‚С‹"}</h3>
                <div className="doc-links">
                  <button className="link-btn" onClick={() => openDoc("public-offer", "РџСѓР±Р»РёС‡РЅР°СЏ РѕС„РµСЂС‚Р°")}>{"РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕРµ СЃРѕРіР»Р°С€РµРЅРёРµ"}</button>
                  <button className="link-btn" onClick={() => openDoc("privacy-policy", "РџРѕР»РёС‚РёРєР° РєРѕРЅС„РёРґРµРЅС†РёР°Р»СЊРЅРѕСЃС‚Рё")}>{"РџРѕР»РёС‚РёРєР° РєРѕРЅС„РёРґРµРЅС†РёР°Р»СЊРЅРѕСЃС‚Рё"}</button>
                  <button className="link-btn" onClick={() => openDoc("acceptable-use", "РџСЂР°РІРёР»Р° РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ")}>{"РџСЂР°РІРёР»Р° РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ"}</button>
                </div>
              </article>
            )}
            {!!docHtml && (
              <article ref={docCardRef} className="card">
                <div className="row between">
                  <h3>{docTitle}</h3>
                  <button onClick={closeDoc}>{"РќР°Р·Р°Рґ"}</button>
                </div>
                <div className="doc-view" dangerouslySetInnerHTML={{ __html: docHtml }} />
              </article>
            )}

            <article className="card support-card">
              <h3>{"РџРѕРґРґРµСЂР¶РєР°"}</h3>
              <p className="muted">{"РџРѕРјРѕР¶РµРј СЃ РїРѕРґРєР»СЋС‡РµРЅРёРµРј, РѕС€РёР±РєР°РјРё РґРѕСЃС‚СѓРїР°, РІРѕРїСЂРѕСЃР°РјРё РїРѕ РѕРїР»Р°С‚Рµ Рё РїСЂРѕРґР»РµРЅРёСЋ."}</p>
              <ul className="support-list">
                <li><strong>{"РљРѕРіРґР° РѕР±СЂР°С‰Р°С‚СЊСЃСЏ:"}</strong> {"РµР¶РµРґРЅРµРІРЅРѕ, 10:00-22:00 РњРЎРљ."}</li>
                <li><strong>{"Р§С‚Рѕ СЂРµС€Р°РµРј:"}</strong> {"РЅР°СЃС‚СЂРѕР№РєР° VPN, РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёРµ РґРѕСЃС‚СѓРїР°, РІРѕРїСЂРѕСЃС‹ РїРѕ РїРѕРґРїРёСЃРєРµ Рё РїР»Р°С‚РµР¶Р°Рј."}</li>
                <li><strong>{"РљСѓРґР°:"}</strong> <a href={SUPPORT_URL} target="_blank" rel="noreferrer">{SUPPORT_URL}</a></li>
              </ul>
              <div className="support-note">{"РџСЂРё РЅР°Р¶Р°С‚РёРё РєРЅРѕРїРєРё РѕС‚РєСЂРѕРµС‚СЃСЏ Telegram СЃ СѓР¶Рµ Р·Р°РїРѕР»РЅРµРЅРЅС‹Рј СЃРѕРѕР±С‰РµРЅРёРµРј: Telegram ID, СЃС‚Р°С‚СѓСЃ РїРѕРґРїРёСЃРєРё, РґР°С‚С‹ Рё СЃСЃС‹Р»РєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё."}</div>
              <button onClick={openSupportChat}>{"РќР°РїРёСЃР°С‚СЊ РІ РїРѕРґРґРµСЂР¶РєСѓ"}</button>
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


