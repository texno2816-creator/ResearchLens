let openAccess = false;
let advancedOpen = false;
let currentQuery = "";

function toggleOA() {
  openAccess = !openAccess;
  document.getElementById("oaToggle").classList.toggle("on", openAccess);
}

function toggleAdvanced() {
  advancedOpen = !advancedOpen;
  const el = document.getElementById("advancedFilters");
  el.style.display = advancedOpen ? "grid" : "none";
  document.getElementById("advToggleLabel").textContent =
    advancedOpen ? "⚙️ Hide filters" : "⚙️ Advanced filters";
}

function fitClass(score) {
  if (score >= 65) return "fit-high";
  if (score >= 35) return "fit-mid";
  return "fit-low";
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast("Copied!");
  });
}

function showToast(msg) {
  const t = document.createElement("div");
  t.textContent = msg;
  t.style.cssText = "position:fixed;bottom:24px;right:24px;background:#6366f1;color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;z-index:999;animation:fadeIn 0.2s";
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2000);
}

async function openDeepAnalysis(title, abstract) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalBody").innerHTML = `
    <div class="status">
      <div class="status-icon">⏳</div>
      <div class="status-text">Analysing paper...<br>This takes 10–15 seconds</div>
    </div>`;
  document.getElementById("modalOverlay").classList.add("open");

  const params = new URLSearchParams({ title, abstract, query: currentQuery });
  const res = await fetch(`/deep_analysis?${params}`);
  const data = await res.json();

  if (data.error) {
    document.getElementById("modalBody").innerHTML = `<div class="status"><div class="status-text">Analysis failed. Try again.</div></div>`;
    return;
  }

  document.getElementById("modalBody").innerHTML = `
    <div class="deep-section">
      <div class="deep-label">Research Question</div>
      <div class="deep-text">${data.research_question || "—"}</div>
    </div>
    <div class="deep-section">
      <div class="deep-label">Methodology</div>
      <div class="deep-text">${data.methodology || "—"}</div>
    </div>
    <div class="deep-section">
      <div class="deep-label">Key Findings</div>
      <ul class="deep-list">
        ${(data.key_findings || []).map(f => `<li>${f}</li>`).join("")}
      </ul>
    </div>
    <div class="deep-section">
      <div class="deep-label">Limitations</div>
      <ul class="deep-list">
        ${(data.limitations || []).map(l => `<li>${l}</li>`).join("")}
      </ul>
    </div>
    <div class="deep-section">
      <div class="deep-label">Best Used For</div>
      <span class="deep-badge">${data.best_used_for || "—"}</span>
    </div>
    <div class="analysis-note">📋 ${data.analysis_based_on || "Abstract only"}</div>
  `;
}

function closeModal() {
  document.getElementById("modalOverlay").classList.remove("open");
}

async function doSearch() {
  const query = document.getElementById("query").value.trim();
  if (!query) return;
  currentQuery = query;

  const btn = document.getElementById("searchBtn");
  btn.disabled = true;
  btn.textContent = "Searching...";
  document.getElementById("loadingBar").classList.add("active");
  document.getElementById("resultsHeader").style.display = "none";
  document.getElementById("results").innerHTML = `
    <div class="status">
      <div class="status-icon">⏳</div>
      <div class="status-text">Searching across databases and generating AI summaries...<br>This takes 20–40 seconds</div>
    </div>`;

  const params = new URLSearchParams({
    query,
    year_start: document.getElementById("year_start").value,
    year_end: document.getElementById("year_end").value,
    min_citations: document.getElementById("min_citations").value || 0,
    open_access: openAccess
  });

  try {
    const res = await fetch(`/search?${params}`);
    const papers = await res.json();

    document.getElementById("loadingBar").classList.remove("active");
    btn.disabled = false;
    btn.textContent = "Search";

    if (!papers.length) {
      document.getElementById("results").innerHTML = `
        <div class="status">
          <div class="status-icon">🔍</div>
          <div class="status-text">No results found. Try a different query.</div>
        </div>`;
      return;
    }

    document.getElementById("resultsCount").textContent = papers.length;
    document.getElementById("resultsHeader").style.display = "flex";

    document.getElementById("results").innerHTML = papers.map(p => `
      <div class="card">
        <div class="card-top">
          <div class="card-title-wrap">
            <div class="card-title">
              ${p.doi_url ? `<a href="${p.doi_url}" target="_blank">${p.title}</a>` : p.title}
            </div>
            ${p.venue ? `<div class="card-venue">${p.venue}</div>` : ""}
          </div>
          <div class="scores-wrap">
            <div class="score-box ${fitClass(p.fit_score)}">
              ${p.fit_score}<span>Fit</span>
            </div>
            <div class="score-box cred-box">
              ${p.credibility}/10<span>Cred</span>
            </div>
          </div>
        </div>

        <div class="card-meta">
          ${p.year ? `<span class="badge badge-year">📅 ${p.year}</span>` : ""}
          <span class="badge badge-cite">📊 ${p.citations} citations</span>
          ${p.pdf_url ? `<a href="${p.pdf_url}" target="_blank" class="badge badge-pdf">📄 PDF</a>` : ""}
          <span class="badge badge-source">${p.source}</span>
          ${p.authors && p.authors.length ? `<span style="font-size:12px;color:#475569">${p.authors.join(", ")}</span>` : ""}
        </div>

        ${p.summary && p.summary !== "Саммари недоступно." ? `
          <div class="ai-summary">
            <div class="ai-summary-label">🤖 AI Summary</div>
            ${p.summary}
          </div>` : ""}

        ${p.abstract ? `<div class="card-abstract">${p.abstract.slice(0, 400)}${p.abstract.length > 400 ? "..." : ""}</div>` : ""}

        <div class="card-actions">
          <button class="action-btn primary" onclick='openDeepAnalysis(${JSON.stringify(p.title)}, ${JSON.stringify(p.abstract || "")})'>
            🔍 Deep Analysis
          </button>
          <button class="action-btn" onclick='copyText(${JSON.stringify(p.apa)})'>
            Copy APA
          </button>
          <button class="action-btn" onclick='copyText(${JSON.stringify(p.bibtex)})'>
            Copy BibTeX
          </button>
        </div>
      </div>
    `).join("");

  } catch (e) {
    document.getElementById("loadingBar").classList.remove("active");
    btn.disabled = false;
    btn.textContent = "Search";
    document.getElementById("results").innerHTML = `
      <div class="status">
        <div class="status-icon">⚠️</div>
        <div class="status-text">Connection error. Check VPN and try again.</div>
      </div>`;
  }
}

document.getElementById("query").addEventListener("keydown", e => {
  if (e.key === "Enter") doSearch();
});