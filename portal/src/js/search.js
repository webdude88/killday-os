// One search box across PDF and portal text (Pagefind) and every ZIM (kiwix-serve).
let pagefind = null;

async function pagefindResults(query) {
  try {
    pagefind = pagefind || (await import("/pagefind/pagefind.js"));
    const found = await pagefind.search(query);
    const data = await Promise.all(found.results.slice(0, 15).map((r) => r.data()));
    return data.map((d) => ({
      title: d.meta.title || d.url,
      url: d.meta.target || d.url,
      excerpt: d.excerpt,
      source: d.meta.source || "Almanac guide",
      warn: d.meta.warn === "yes",
    }));
  } catch (err) {
    console.warn("pagefind unavailable", err);
    return [];
  }
}

async function kiwixResults(query) {
  try {
    const url = `kiwix/search?pattern=${encodeURIComponent(query)}&pageLength=25&format=xml`;
    const text = await fetch(url).then((r) => r.text());
    const doc = new DOMParser().parseFromString(text, "text/xml");
    return [...doc.querySelectorAll("item")].map((node) => ({
      title: node.querySelector("title")?.textContent || "Untitled",
      url: (node.querySelector("link")?.textContent || "").replace(/^\//, ""),
      excerpt: KD.esc(node.querySelector("description")?.textContent || ""),
      source: node.querySelector("book title")?.textContent || "Encyclopedia",
      warn: false,
    }));
  } catch (err) {
    console.warn("kiwix search unavailable", err);
    return [];
  }
}

async function runSearch(query) {
  const box = document.getElementById("results");
  box.innerHTML = `<p class="hint">Digging through the archive for "${KD.esc(query)}"...</p>`;
  const [guides, articles] = await Promise.all([pagefindResults(query), kiwixResults(query)]);
  const combined = [...guides, ...articles];
  window.kdLastResultCount = combined.length;
  document.body.dataset.searchDone = String(combined.length);
  if (!combined.length) {
    box.innerHTML = `<p class="hint">Corrupted? Still alive. Nothing matched "${KD.esc(query)}". Try fewer or simpler words.</p>`;
    return;
  }
  box.innerHTML = combined.map((r) => `
    <div class="result">
      <a href="${KD.esc(r.url)}">${KD.esc(r.title)}</a>
      <div class="source">${KD.esc(r.source)}${r.warn ? ' &middot; <span class="tag warn">Reference only</span>' : ""}</div>
      <p>${r.excerpt}</p>
    </div>`).join("");
}

function renderTiles() {
  const tiles = document.getElementById("tiles");
  const moduleTiles = KD.catalog.modules.map((mod) => {
    const present = mod.items.filter(KD.isInstalled).length;
    return `<a class="tile ${present ? "" : "missing"}" href="module.html?id=${encodeURIComponent(mod.id)}">
      <h3>${KD.esc(mod.title)}</h3><p>${KD.esc(mod.blurb)}</p>
      <span class="tag">${present} of ${mod.items.length} installed</span>
      ${mod.disclaimer && mod.disclaimer !== "general" ? '<span class="tag warn">Reference only</span>' : ""}
    </a>`;
  });
  const mapTile = `<a class="tile" href="map.html"><h3>Offline map</h3><p>Streets, terrain names and places. No internet needed.</p>
      <span class="tag">${KD.status.maps.length} region file(s)</span></a>`;
  tiles.innerHTML = [mapTile, ...moduleTiles].join("");
}

(async function init() {
  KD.header();
  await KD.load();
  renderTiles();
  const form = document.getElementById("searchform");
  const input = document.getElementById("q");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = input.value.trim();
    if (query) {
      history.replaceState(null, "", `?q=${encodeURIComponent(query)}`);
      runSearch(query);
    }
  });
  const initial = new URLSearchParams(location.search).get("q");
  if (initial) {
    input.value = initial;
    runSearch(initial);
  }
  input.focus();
})();
