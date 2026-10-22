/* visitor-dashboard: tells the site what only the browser knows about this visit.
   Screen, phone model, time zone, time spent, how far the page was read, and the clicks
   (buttons, links, downloads; name one yourself with data-track="..."). No cookies of its own. */
(function () {
  var me = document.currentScript;
  if (!me || !me.dataset.v) return;
  var url = me.dataset.u, base = { v: +me.dataset.v, k: me.dataset.k };
  var started = Date.now(), hidden = 0, hiddenAt = 0, deepest = 0, queue = [], first = true;

  function send(extra, useBeacon) {
    var body = JSON.stringify(Object.assign({}, base, extra));
    if (useBeacon && navigator.sendBeacon) {
      if (navigator.sendBeacon(url, new Blob([body], { type: "text/plain" }))) return;
    }
    try { fetch(url, { method: "POST", body: body, keepalive: true, headers: { "Content-Type": "text/plain" } }); } catch (e) {}
  }
  function seen() { return Math.round((Date.now() - started - hidden - (hiddenAt ? Date.now() - hiddenAt : 0)) / 1000); }
  function scrolled() {
    var page = document.documentElement, height = page.scrollHeight - window.innerHeight;
    deepest = Math.max(deepest, height <= 0 ? 100 : Math.round(100 * (window.scrollY || page.scrollTop) / height));
    return Math.min(deepest, 100);
  }
  function report(useBeacon) {
    var extra = { d: seen(), s: scrolled(), e: queue.splice(0, 50) };
    if (first) { Object.assign(extra, about()); first = false; }
    send(extra, useBeacon);
  }
  function about() {
    var s = window.screen || {}, c = navigator.connection || {};
    var info = {
      screen: s.width + "×" + s.height, viewport: window.innerWidth + "×" + window.innerHeight,
      dpr: window.devicePixelRatio || 1, lang: navigator.language || "", conn: c.effectiveType || "",
      title: document.title || "", touch: navigator.maxTouchPoints || 0,
      dark: window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? 1 : 0,
      ipad: /Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1 ? 1 : 0
    };
    try { info.tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    return info;
  }

  // the phone's model and the system version (Chrome, Edge, Samsung Internet: the User-Agent hides them now)
  if (navigator.userAgentData && navigator.userAgentData.getHighEntropyValues) {
    navigator.userAgentData.getHighEntropyValues(["model", "platformVersion"]).then(function (h) {
      if (h.model || h.platformVersion) send({ model: h.model || "", os_ver: h.platformVersion || "" });
    }).catch(function () {});
  }

  document.addEventListener("click", function (event) {
    var el = event.target.closest && event.target.closest("[data-track],a,button,summary,[role=button],input[type=submit]");
    if (!el) return;
    var href = el.getAttribute("href") || "", kind = "click";
    if (el.tagName === "A" && href) {
      if (/\.(pdf|docx?|xlsx?|zip|rar|apk|mp4|mp3|png|jpe?g)(\?|$)/i.test(href) || el.hasAttribute("download")) kind = "download";
      else if (/^(mailto|tel|https?:\/\/(wa\.me|t\.me))/i.test(href)) kind = "contact";
      else if (el.host && el.host !== location.host) kind = "outbound";
      else kind = "link";
    }
    var label = el.getAttribute("data-track") || el.getAttribute("aria-label") || el.getAttribute("title") ||
      (el.innerText || el.value || "").replace(/\s+/g, " ").trim() || href;
    queue.push({ t: Date.now() / 1000, k: kind, l: label.slice(0, 120), h: href.slice(0, 300) });
    if (kind !== "click") report(true); // the visitor may be leaving
  }, true);

  window.addEventListener("scroll", scrolled, { passive: true });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") { hiddenAt = Date.now(); report(true); }
    else if (hiddenAt) { hidden += Date.now() - hiddenAt; hiddenAt = 0; }
  });
  window.addEventListener("pagehide", function () { report(true); });
  setTimeout(function () { report(false); }, 1500);
  setInterval(function () { if (document.visibilityState === "visible") report(false); }, 30000);
})();
