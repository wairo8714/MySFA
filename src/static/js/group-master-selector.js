function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

document.addEventListener("DOMContentLoaded", () => {
  const openLinks = Array.from(document.querySelectorAll(".js-open-group-master"));
  const overlay = document.getElementById("group-master-modal-overlay");
  const modal = document.getElementById("group-master-modal");
  const closeBtn = document.getElementById("group-master-modal-close");
  const results = document.getElementById("group-master-modal-results");
  const empty = document.getElementById("group-master-modal-empty");

  if (!openLinks.length || !overlay || !modal || !closeBtn || !results || !empty) return;

  let mode = null;
  let cachedGroups = null;

  function openModal(nextMode) {
    mode = nextMode;
    overlay.classList.add("is-open");
    modal.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    modal.setAttribute("aria-hidden", "false");
    renderGroups(cachedGroups);
    if (!cachedGroups) loadGroups();
  }

  function closeModal() {
    overlay.classList.remove("is-open");
    modal.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
    modal.setAttribute("aria-hidden", "true");
    mode = null;
  }

  function buildTargetUrl(customId) {
    if (mode === "group") {
      return `/mysfa/group/${encodeURIComponent(customId)}/`;
    }
    return mode === "industry"
      ? `/mysfa/group/${encodeURIComponent(customId)}/industry-master/`
      : `/mysfa/group/${encodeURIComponent(customId)}/product-master/`;
  }

  function renderGroups(groups) {
    results.innerHTML = "";
    if (!Array.isArray(groups) || groups.length === 0) {
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";

    for (const g of groups) {
      const cid = g?.custom_id;
      const name = g?.name || "";
      if (!cid) continue;

      const li = document.createElement("li");
      li.className = "group-master-result";
      li.innerHTML = `<button type="button" class="group-master-result-btn" data-custom-id="${escapeHtml(
        cid
      )}">
        <span class="group-master-result__name">${escapeHtml(name || cid)}</span>
        <span class="group-master-result__id">${escapeHtml(cid)}</span>
      </button>`;
      results.appendChild(li);
    }
  }

  async function loadGroups() {
    try {
      const res = await fetch("/mysfa/api/my-groups/", {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!res.ok) {
        renderGroups([]);
        return;
      }
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        renderGroups([]);
        return;
      }
      const data = await res.json();
      const list = Array.isArray(data.results) ? data.results : [];
      cachedGroups = list;
      renderGroups(cachedGroups);
    } catch (_) {
      renderGroups([]);
    }
  }

  openLinks.forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const kind = a.getAttribute("data-master-kind");
      if (kind === "industry") return openModal("industry");
      if (kind === "group") return openModal("group");
      return openModal("product");
    });
  });

  closeBtn.addEventListener("click", closeModal);
  overlay.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  results.addEventListener("click", (e) => {
    const btn = e.target?.closest?.(".group-master-result-btn");
    if (!btn || !mode) return;
    const customId = btn.getAttribute("data-custom-id");
    if (!customId) return;
    window.location.href = buildTargetUrl(customId);
  });
});

