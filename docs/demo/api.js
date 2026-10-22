/* The dashboard's API, answered in the browser for the demo (no server). Mirrors visitor_dashboard/core.py:
   Tracker.chosen (filters), stats, row, visits, detail and export, over the made-up visits in data.js.
   A new visit arrives every ~40 seconds so the demo looks live. */
(function () {
  const D = window.DEMO, NOW = () => Date.now() / 1000;
  const loaded = NOW();
  const FILTERS = ["country_code", "city", "device", "os", "browser", "brand", "source", "path", "app", "isp", "lang", "screen", "visitor"];
  const ICON = { mobile: "📱", desktop: "💻", tablet: "📲", bot: "🤖" };
  const RANGES = { today: 0, 1: 1, 7: 7, 30: 30, 90: 90, 365: 365, all: null };

  function expand(cells) {
    const r = {};
    D.columns.forEach((c, i) => { r[c] = cells[i]; });
    const a = D.agents[r.agent], p = r.place >= 0 ? D.places[r.place] : { country_code: "", country: "", region: "", city: "", isp: "Google LLC", lat: null, lon: null, lang: "", tz: "" };
    Object.assign(r, { ts: loaded + r.ts, host: D.host, ua: a.ua, device: a.device, os: a.os, os_ver: a.os_ver, browser: a.browser,
      browser_ver: a.browser_ver, brand: a.brand, model: a.model, app: a.app, country_code: p.country_code, country: p.country,
      region: p.region, city: p.city, isp: p.isp, lat: p.lat, lon: p.lon, lang: r.bot ? "" : p.lang, tz: r.bot ? "" : p.tz,
      screen: a.screen, viewport: a.screen, dpr: a.device === "desktop" ? 1 : 3, touch: a.device === "desktop" ? 0 : 5, clicks: 0 });
    r.last = r.ts + r.duration;
    return r;
  }
  const rows = D.rows.map(expand);
  const byId = new Map(rows.map((r) => [r.id, r]));
  const events = D.events.map(([id, offset, kind, label, target]) => ({ visit_id: id, ts: byId.get(id).ts + offset, kind, label, target }));
  events.forEach((e) => { byId.get(e.visit_id).clicks += 1; });

  // a new visitor now and then
  setInterval(() => {
    const humans = rows.filter((r) => !r.bot && r.place >= 0).slice(0, 400);
    const like = humans[Math.floor(Math.random() * humans.length)];
    const fresh = Math.random() < 0.6;
    const r = Object.assign({}, like, { id: rows[0].id + 1, ts: NOW(), duration: 0, scroll: 0, clicks: 0, new_visitor: fresh ? 1 : 0,
      visitor: fresh ? "live" + Date.now() : like.visitor, session: "live" + Date.now(), path: "/", title: "Jane Doe · Python developer" });
    r.last = r.ts;
    rows.unshift(r); byId.set(r.id, r);
  }, 40000);

  // ---- i18n.py ----
  const W = (lang) => D.words[lang] || D.words.en;
  const OLD = { "Local network": "local" };
  const t = (lang, key, values = {}) => (W(lang)[key] ?? D.words.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => values[k] ?? "");
  const word = (lang, v) => { v = OLD[v] || v || ""; return v in D.words.en ? t(lang, v) : v; };
  const country = (lang, code, saved) => (lang === "ar" ? D.ar_countries[(code || "").toUpperCase()] || saved || "" : saved || "");
  const place = (lang, name) => {
    name = name || "";
    if (lang !== "ar") return name;
    const plain = name.toLowerCase().replace(" governorate", "").replace(" province", "").replace(/-/g, " ").replace(/'/g, "");
    return D.ar_cities[plain] || name;
  };
  const ago = (lang, s) => s < 60 ? t(lang, "now") : s < 3600 ? t(lang, "minutes", { n: Math.floor(s / 60) })
    : s < 86400 ? t(lang, "hours", { n: Math.floor(s / 3600) }) : t(lang, "days", { n: Math.floor(s / 86400) });
  const flag = (code) => /^[A-Za-z]{2}$/.test(code || "") ? String.fromCodePoint(...[...code.toUpperCase()].map((c) => 0x1F1E6 + c.charCodeAt(0) - 65)) : "";

  // ---- times, in the viewer's own time zone ----
  const pad = (n) => String(n).padStart(2, "0");
  const day = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const stamp = (ts) => { const d = new Date(ts * 1000); return `${day(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  const clock = (ts) => { const d = new Date(ts * 1000); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };

  // ---- Tracker.chosen ----
  function chosen(q) {
    const days = q.range in RANGES ? RANGES[q.range] : 7;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    let since = days === null ? 0 : today.getTime() / 1000 - Math.max(days - 1, 0) * 86400;
    let picked = rows.filter((r) => r.ts >= since);
    if (q.bots !== "1") picked = picked.filter((r) => !r.bot);
    for (const name of FILTERS) if (q[name]) picked = picked.filter((r) => String(r[name] ?? "") === q[name]);
    if (q.new === "1") picked = picked.filter((r) => r.new_visitor);
    const needle = (q.q || "").trim().toLowerCase();
    if (needle) picked = picked.filter((r) => ["ip", "city", "country", "isp", "path", "ua", "source", "model", "referrer"]
      .some((k) => String(r[k] ?? "").toLowerCase().includes(needle)));
    if (days === null) since = picked.length ? Math.min(...picked.map((r) => r.ts)) : NOW();
    return { picked, since };
  }

  function top(picked, key, label, n = 10) {
    const counts = new Map();
    for (const r of picked) { const k = String(r[key] ?? ""); if (k) counts.set(k, (counts.get(k) || 0) + 1); }
    return [...counts].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, c]) => ({ value: k, label: label ? label(k) : k, n: c }));
  }

  function stats(q, L) {
    const { picked, since } = chosen(q), now = NOW();
    const visitors = new Set(picked.map((r) => r.visitor));
    const sessions = new Map();
    picked.forEach((r) => sessions.set(r.session, (sessions.get(r.session) || 0) + 1));
    const durations = picked.filter((r) => r.duration).map((r) => r.duration);
    const perDay = new Map(), hours = Array(24).fill(0);
    for (let d = new Date(since * 1000); d <= new Date(); d.setDate(d.getDate() + 1)) perDay.set(day(d), [0, new Set()]);
    perDay.set(day(new Date()), perDay.get(day(new Date())) || [0, new Set()]);
    for (const r of picked) {
      const d = new Date(r.ts * 1000), k = day(d);
      if (!perDay.has(k)) perDay.set(k, [0, new Set()]);
      perDay.get(k)[0] += 1; perDay.get(k)[1].add(r.visitor); hours[d.getHours()] += 1;
    }
    const names = {};
    picked.forEach((r) => { if (r.country_code) names[r.country_code] = r.country; });
    const online = new Set(rows.filter((r) => !r.bot && now - r.last < 300).map((r) => r.visitor));
    const clickCounts = new Map();
    for (const e of events) {
      if (e.ts < since || byId.get(e.visit_id).bot) continue;
      const k = e.kind + "\u0000" + e.label;
      clickCounts.set(k, (clickCounts.get(k) || 0) + 1);
    }
    const points = new Map();
    for (const r of picked) if (r.lat != null) { const k = r.lat + "," + r.lon; const p = points.get(k) || { lat: r.lat, lon: r.lon, city: place(L, r.city), n: 0 }; p.n += 1; points.set(k, p); }
    const sessionCounts = [...sessions.values()];
    return {
      kpi: { visits: picked.length, visitors: visitors.size, new: new Set(picked.filter((r) => r.new_visitor).map((r) => r.visitor)).size,
        avg_duration: durations.length ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length) : 0,
        bounce: sessionCounts.length ? Math.round(100 * sessionCounts.filter((n) => n === 1).length / sessionCounts.length) : 0,
        per_visitor: visitors.size ? Math.round(10 * picked.length / visitors.size) / 10 : 0, online: online.size },
      days: [...perDay].sort().map(([d, v]) => ({ day: d, visits: v[0], visitors: v[1].size })),
      hours,
      devices: top(picked, "device", (k) => word(L, k)), os: top(picked, "os"), browsers: top(picked, "browser"),
      brands: top(picked, "brand"), apps: top(picked, "app"),
      countries: top(picked, "country_code", (k) => `${flag(k)} ${country(L, k, names[k] || k)}`),
      cities: top(picked, "city", (k) => place(L, k)), isps: top(picked, "isp"), pages: top(picked, "path"),
      sources: top(picked, "source", (k) => word(L, k)), languages: top(picked, "lang"), screens: top(picked, "screen"),
      clicks: [...clickCounts].sort((a, b) => b[1] - a[1]).slice(0, 15).map(([k, n]) => { const [kind, label] = k.split("\u0000"); return { label: label || kind, kind, n }; }),
      points: [...points.values()].sort((a, b) => b.n - a.n).slice(0, 300),
    };
  }

  function row(r, L) {
    return { id: r.id, time: stamp(r.ts), ago: ago(L, NOW() - r.ts), flag: flag(r.country_code), country: country(L, r.country_code, r.country),
      country_code: r.country_code, city: place(L, r.city), region: place(L, r.region), isp: r.isp, ip: r.ip, device: r.device,
      device_label: word(L, r.device), icon: ICON[r.device] || "", os: `${r.os || ""} ${r.os_ver || ""}`.trim(),
      browser: `${r.browser || ""} ${r.browser_ver || ""}`.trim(), model: `${r.brand || ""} ${r.model || ""}`.trim(), app: r.app,
      source: word(L, r.source), path: r.path, title: r.title, duration: Math.round(r.duration || 0), scroll: r.scroll, clicks: r.clicks,
      new: !!r.new_visitor, bot: !!r.bot, visitor: r.visitor, online: NOW() - r.last < 300 };
  }

  function detail(id, L) {
    const r = byId.get(id);
    if (!r) return null;
    const mine = rows.filter((x) => x.visitor === r.visitor);
    return Object.assign(row(r, L), { referrer: r.referrer, query: r.query, ua: r.ua, lang: r.lang, screen: r.screen, viewport: r.viewport,
      dpr: r.dpr, tz: r.tz, conn: r.conn, dark: r.dark, touch: r.touch, lat: r.lat, lon: r.lon, host: r.host, session: r.session,
      visitor_visits: mine.length, first_seen: stamp(Math.min(...mine.map((x) => x.ts))),
      events: events.filter((e) => e.visit_id === id).sort((a, b) => a.ts - b.ts).map((e) => ({ time: clock(e.ts), kind: e.kind, label: e.label, target: e.target })),
      history: mine.slice(0, 50).map((h) => ({ id: h.id, time: stamp(h.ts), path: h.path, source: word(L, h.source), duration: Math.round(h.duration || 0) })) });
  }

  function csv(q) {
    const cols = ["id", "time", "visitor", "session", "new_visitor", "ip", "host", "path", "query", "title", "referrer", "source", "ua",
      "device", "os", "os_ver", "browser", "browser_ver", "brand", "model", "app", "bot", "lang", "country_code", "country", "region",
      "city", "isp", "lat", "lon", "screen", "tz", "conn", "dark", "duration", "scroll", "clicks"];
    const cell = (v) => { v = v == null ? "" : String(v); return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; };
    const lines = chosen(q).picked.map((r) => cols.map((c) => cell(c === "time" ? stamp(r.ts) : r[c])).join(","));
    return "﻿" + [cols.join(","), ...lines].join("\r\n");
  }

  const json = (value, status = 200) => Promise.resolve(new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } }));
  const realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = new URL(typeof input === "string" ? input : input.url, location.href);
    if (!url.pathname.startsWith("/visits/api/")) return realFetch(input, init);
    const q = Object.fromEntries(url.searchParams), L = q.ui === "ar" ? "ar" : "en", sub = url.pathname.slice("/visits/api/".length);
    if (sub === "stats") return json(stats(q, L));
    if (sub === "visits") {
      const picked = chosen(q).picked, offset = Math.max(parseInt(q.offset || "0", 10) || 0, 0);
      return json({ total: picked.length, visits: picked.slice(offset, offset + 50).map((r) => row(r, L)) });
    }
    if (sub.startsWith("visit/")) { const found = detail(parseInt(sub.slice(6), 10), L); return found ? json(found) : json({}, 404); }
    return json({}, 404);
  };

  // CSV export: made here instead of downloaded from the server
  document.addEventListener("click", (e) => {
    const link = e.target.closest && e.target.closest("#csv");
    if (!link) return;
    e.preventDefault();
    const q = Object.fromEntries(new URL(link.href, location.href).searchParams);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv(q)], { type: "text/csv" }));
    a.download = "visits-demo.csv";
    a.click();
  }, true);
})();
