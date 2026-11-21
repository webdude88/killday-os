// Shared header, catalog loading and helpers for every Almanac page.
const KD = {
  catalog: null,
  status: { installed: [], maps: [], kiwix: false, persistence: false },
  esc(text) {
    const node = document.createElement("div");
    node.textContent = text == null ? "" : text;
    return node.innerHTML;
  },
  header() {
    document.body.insertAdjacentHTML("afterbegin", `
      <header class="top">
        <a class="brand" href="index.html"><img src="img/killday-skull-128.png" alt="">
          <span><span class="wordmark">KILL<span class="hy">-</span>DAY OS</span><br><span class="tagline">The Kill-Day Almanac</span></span></a>
        <nav class="links"><a href="index.html">Search</a><a href="start-here.html">Start here</a><a href="map.html">Map</a><a href="about.html">About</a></nav>
      </header>`);
  },
  async load() {
    KD.catalog = await fetch("catalog.json").then((r) => r.json());
    try {
      KD.status = await fetch("api/status").then((r) => r.json());
    } catch (err) {
      console.warn("status unavailable", err);
    }
  },
  allItems() {
    return KD.catalog.modules.flatMap((mod) => mod.items.map((item) => ({ ...item, module: mod })));
  },
  disclaimerText(item, mod) {
    const kind = item.disclaimer || mod.disclaimer || "general";
    return KD.catalog.disclaimers[kind];
  },
  itemLink(item) {
    if (item.kind === "zim") {
      return `kiwix/content/${encodeURIComponent(item.path.replace(/^zim\//, "").replace(/\.zim$/, ""))}/`;
    }
    return `read.html?id=${encodeURIComponent(item.id)}`;
  },
  isInstalled(item) {
    return KD.status.installed.includes(item.id);
  },
};
