const DEFAULT_API_BASE = (() => {
  if (typeof window !== "undefined" && window.API_BASE) {
    return window.API_BASE;
  }
  return "http://localhost:8000";
})();

let apiBase = "";

const elements = {};

function cacheElements() {
  elements.apiBaseInput = document.getElementById("apiBase");
  elements.saveApiBase = document.getElementById("saveApiBase");
  elements.healthStatus = document.getElementById("healthStatus");
  elements.ingestForm = document.getElementById("ingestForm");
  elements.ingestStatus = document.getElementById("ingestStatus");
  elements.ingestProjectId = document.getElementById("ingestProjectId");
  elements.zipUpload = document.getElementById("zipUpload");
  elements.folderPath = document.getElementById("folderPath");
  elements.ocrToggle = document.getElementById("ocrToggle");
  elements.refreshProjects = document.getElementById("refreshProjects");
  elements.projectsTable = document.getElementById("projectsTable");
  elements.askForm = document.getElementById("askForm");
  elements.askStatus = document.getElementById("askStatus");
  elements.askProjectId = document.getElementById("askProjectId");
  elements.question = document.getElementById("question");
  elements.topK = document.getElementById("topK");
  elements.answer = document.getElementById("answer");
  elements.projectRowTemplate = document.getElementById("projectRowTemplate");
  elements.citationTemplate = document.getElementById("citationTemplate");
}

function sanitizeBase(url) {
  if (!url) return "";
  const trimmed = url.trim();
  if (!trimmed) return "";
  return trimmed.replace(/\/$/, "");
}

function setStatus(element, message, level = "") {
  if (!element) return;
  element.textContent = message || "";
  element.className = "status";
  if (message && level) {
    element.classList.add(level);
  }
}

function setApiBase(next) {
  apiBase = sanitizeBase(next);
  if (apiBase) {
    localStorage.setItem("apiBase", apiBase);
  } else {
    localStorage.removeItem("apiBase");
  }
  elements.apiBaseInput.value = apiBase;
}

function getApiBase() {
  return apiBase;
}

async function fetchJson(path, options = {}) {
  const base = getApiBase();
  if (!base) {
    throw new Error("API base URL is not configured");
  }
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`Unexpected response: ${text}`);
  }
}

function renderHealth(data) {
  const container = elements.healthStatus;
  container.className = "status success";
  container.innerHTML = "";
  if (!data) {
    container.textContent = "Health check returned no payload.";
    return;
  }
  const strip = document.createElement("div");
  strip.className = "badge-strip";
  const badges = [
    { label: "API reachable", ok: true },
    { label: "Chroma writable", ok: Boolean(data.chroma) },
    { label: "OCR detected", ok: Boolean(data.ocr) },
  ];
  badges.forEach((item) => {
    const badge = document.createElement("span");
    badge.className = `badge ${item.ok ? "ok" : "warn"}`;
    badge.textContent = `${item.ok ? "✅" : "⚠️"} ${item.label}`;
    strip.appendChild(badge);
  });
  container.appendChild(strip);
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.append("Embedding model: ");
  const code = document.createElement("code");
  code.textContent = data.embedding_model || "unknown";
  meta.appendChild(code);
  meta.append(" • Docs indexed: ");
  const strong = document.createElement("strong");
  strong.textContent = `${data.docs_indexed ?? "0"}`;
  meta.appendChild(strong);
  container.appendChild(meta);
}

async function refreshHealth() {
  if (!getApiBase()) {
    setStatus(elements.healthStatus, "Set API base URL to check status.", "info");
    return;
  }
  setStatus(elements.healthStatus, "Pinging /healthz…", "info");
  try {
    const data = await fetchJson("/healthz");
    renderHealth(data);
  } catch (error) {
    setStatus(elements.healthStatus, `Health check failed: ${error.message}`, "error");
  }
}

function renderProjects(projects) {
  const container = elements.projectsTable;
  container.innerHTML = "";
  if (!Array.isArray(projects) || projects.length === 0) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "No tracked projects yet. Ingest docs to populate the index.";
    container.appendChild(p);
    return;
  }
  const template = elements.projectRowTemplate;
  projects.forEach((proj) => {
    const fragment = template.content.cloneNode(true);
    fragment.querySelector(".project-id").textContent = proj.project_id;
    fragment.querySelector(".doc-count").textContent = `${proj.docs?.length ?? 0} files`;
    fragment.querySelector(".chunk-count").textContent = `${proj.chunks ?? 0} chunks`;
    fragment
      .querySelector(".doc-list")
      .textContent = Array.isArray(proj.docs) && proj.docs.length ? proj.docs.join(", ") : "—";
    container.appendChild(fragment);
  });
}

async function loadProjects() {
  if (!getApiBase()) {
    elements.projectsTable.innerHTML = "";
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "Set API base URL to query tracked projects.";
    elements.projectsTable.appendChild(p);
    return;
  }
  elements.projectsTable.textContent = "Loading projects…";
  try {
    const projects = await fetchJson("/projects");
    renderProjects(projects);
  } catch (error) {
    elements.projectsTable.textContent = `Failed to load projects: ${error.message}`;
  }
}

function setProjectId(pid) {
  const value = (pid || "").trim();
  elements.ingestProjectId.value = value;
  elements.askProjectId.value = value;
  if (value) {
    localStorage.setItem("projectId", value);
  }
}

function clearAnswer() {
  elements.answer.innerHTML = "";
}

function showAnswer(result, projectId) {
  clearAnswer();
  if (!result) {
    return;
  }
  const answerHeading = document.createElement("h3");
  answerHeading.textContent = "Answer";
  const answerBody = document.createElement("p");
  answerBody.textContent = result.answer || "No answer returned.";
  elements.answer.appendChild(answerHeading);
  elements.answer.appendChild(answerBody);
  const citations = Array.isArray(result.citations) ? result.citations : [];
  if (citations.length === 0) {
    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent = "No citations were returned for this answer.";
    elements.answer.appendChild(hint);
    return;
  }
  const citeHeading = document.createElement("h4");
  citeHeading.textContent = "Citations";
  elements.answer.appendChild(citeHeading);
  const template = elements.citationTemplate;
  citations.forEach((cite) => {
    const fragment = template.content.cloneNode(true);
    const section = fragment.querySelector(".citation");
    const text = section.querySelector(".citation-text");
    const score = typeof cite.score === "number" ? cite.score.toFixed(2) : "n/a";
    text.textContent = `${cite.source} p.${cite.page} (score ${score})`;
    const img = section.querySelector(".citation-preview");
    const params = new URLSearchParams({
      source: cite.source,
      page: String(cite.page),
      project_id: projectId,
    });
    img.src = `${getApiBase()}/page_preview?${params.toString()}&t=${Date.now()}`;
    img.alt = `${cite.source} page ${cite.page}`;
    img.addEventListener("error", () => {
      img.remove();
      const fallback = document.createElement("p");
      fallback.className = "hint";
      fallback.textContent = "Preview unavailable (check API logs).";
      section.appendChild(fallback);
    });
    elements.answer.appendChild(fragment);
  });
}

async function handleIngest(event) {
  event.preventDefault();
  if (!getApiBase()) {
    setStatus(elements.ingestStatus, "Set API base URL before ingesting documents.", "error");
    return;
  }
  const submit = elements.ingestForm.querySelector('button[type="submit"]');
  submit.disabled = true;
  const originalLabel = submit.textContent;
  submit.textContent = "Sending…";
  setStatus(elements.ingestStatus, "Uploading bundle to API…", "info");
  const file = elements.zipUpload.files[0];
  const folder = elements.folderPath.value.trim();
  if (!file && !folder) {
    setStatus(elements.ingestStatus, "Provide a ZIP of PDFs or a server folder path.", "error");
    submit.disabled = false;
    submit.textContent = originalLabel;
    return;
  }
  const formData = new FormData();
  if (file) {
    formData.append("zipfile", file, file.name);
  }
  if (folder) {
    formData.append("folder_path", folder);
  }
  const requestedProjectId = elements.ingestProjectId.value.trim();
  if (requestedProjectId) {
    formData.append("project_id", requestedProjectId);
  }
  formData.append("ocr", elements.ocrToggle.checked ? "true" : "false");
  try {
    const response = await fetch(`${getApiBase()}/ingest`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || response.statusText);
    }
    const data = await response.json();
    setStatus(
      elements.ingestStatus,
      `Ingested ${data.files} files / ${data.pages} pages → ${data.chunks} chunks (project ${data.project_id}).`,
      "success"
    );
    setProjectId(data.project_id);
    await loadProjects();
  } catch (error) {
    setStatus(elements.ingestStatus, `Ingest failed: ${error.message}`, "error");
  } finally {
    submit.disabled = false;
    submit.textContent = originalLabel;
  }
}

async function handleAsk(event) {
  event.preventDefault();
  if (!getApiBase()) {
    setStatus(elements.askStatus, "Set API base URL before asking questions.", "error");
    return;
  }
  const projectId = elements.askProjectId.value.trim();
  const question = elements.question.value.trim();
  const topK = Number(elements.topK.value || 5);
  if (!projectId) {
    setStatus(elements.askStatus, "Project ID is required.", "error");
    return;
  }
  if (!question) {
    setStatus(elements.askStatus, "Enter a question to query the index.", "error");
    return;
  }
  const submit = elements.askForm.querySelector('button[type="submit"]');
  submit.disabled = true;
  const originalLabel = submit.textContent;
  submit.textContent = "Querying…";
  setStatus(elements.askStatus, "Running retrieval…", "info");
  clearAnswer();
  try {
    const payload = {
      project_id: projectId,
      question,
      top_k: Math.max(1, Math.min(50, topK || 5)),
    };
    const result = await fetchJson("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setStatus(elements.askStatus, "Answer ready.", "success");
    showAnswer(result, projectId);
    setProjectId(projectId);
  } catch (error) {
    setStatus(elements.askStatus, `Query failed: ${error.message}`, "error");
  } finally {
    submit.disabled = false;
    submit.textContent = originalLabel;
  }
}

function bindEvents() {
  elements.saveApiBase.addEventListener("click", () => {
    const candidate = elements.apiBaseInput.value.trim();
    if (candidate) {
      try {
        // Throws if URL invalid
        new URL(candidate);
      } catch (error) {
        setStatus(elements.healthStatus, "Enter a full URL including http(s)://", "error");
        return;
      }
    }
    setApiBase(candidate || "");
    if (getApiBase()) {
      refreshHealth();
      loadProjects();
    } else {
      setStatus(elements.healthStatus, "Cleared API base. Set a new endpoint to continue.", "info");
    }
  });

  elements.ingestForm.addEventListener("submit", handleIngest);
  elements.refreshProjects.addEventListener("click", loadProjects);
  elements.askForm.addEventListener("submit", handleAsk);
  elements.askProjectId.addEventListener("change", (event) => setProjectId(event.target.value));
  elements.ingestProjectId.addEventListener("change", (event) => setProjectId(event.target.value));
}

function bootstrap() {
  cacheElements();
  const params = new URLSearchParams(window.location.search);
  const urlOverride = params.get("api");
  const stored = localStorage.getItem("apiBase");
  const initial = sanitizeBase(urlOverride || stored || DEFAULT_API_BASE);
  try {
    if (initial) {
      new URL(initial);
    }
    setApiBase(initial);
  } catch (error) {
    setApiBase(DEFAULT_API_BASE);
  }
  const savedProjectId = localStorage.getItem("projectId");
  if (savedProjectId) {
    setProjectId(savedProjectId);
  }
  bindEvents();
  if (getApiBase()) {
    refreshHealth();
    loadProjects();
  } else {
    setStatus(elements.healthStatus, "Set API base URL to get started.", "info");
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);
