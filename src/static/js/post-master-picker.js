function debounce(fn, waitMs) {
  let t = null;
  return (...args) => {
    if (t) window.clearTimeout(t);
    t = window.setTimeout(() => fn(...args), waitMs);
  };
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

document.addEventListener("DOMContentLoaded", () => {
  const groupSelect = document.getElementById("id_group");
  const productSelect = document.getElementById("id_product");
  const industrySelect = document.getElementById("id_industry");

  const productField = document.getElementById("product-field");
  const industryField = document.getElementById("industry-field");

  const productOpen = document.getElementById("product-open");
  const industryOpen = document.getElementById("industry-open");
  const productSelected = document.getElementById("product-selected");
  const industrySelected = document.getElementById("industry-selected");

  const overlay = document.getElementById("master-modal-overlay");
  const modal = document.getElementById("master-modal");
  const modalTitle = document.getElementById("master-modal-title");
  const modalClose = document.getElementById("master-modal-close");
  const modalSearch = document.getElementById("master-modal-search");
  const modalMasterLink = document.getElementById("master-modal-master-link");
  const modalResults = document.getElementById("master-modal-results");
  const modalEmpty = document.getElementById("master-modal-empty");

  if (
    !groupSelect ||
    !productSelect ||
    !industrySelect ||
    !productOpen ||
    !industryOpen ||
    !productSelected ||
    !industrySelected ||
    !overlay ||
    !modal ||
    !modalTitle ||
    !modalClose ||
    !modalSearch ||
    !modalMasterLink ||
    !modalResults ||
    !modalEmpty
  ) {
    return;
  }

  const groupMap = window.__GROUP_ID_TO_CUSTOM_ID__ || {};
  let mode = null; // "product" | "industry"

  function getSelectedGroupCustomId() {
    const pk = groupSelect.value;
    return pk ? groupMap[String(pk)] : null;
  }

  function setEnabledForMasters(enabled) {
    productSelect.disabled = !enabled; // hidden select (submit用)
    industrySelect.disabled = !enabled; // hidden select (submit用)
    productOpen.disabled = !enabled;
    industryOpen.disabled = !enabled;

    if (productField) {
      productField.classList.toggle("post-master-field--disabled", !enabled);
      productField.setAttribute("aria-disabled", enabled ? "false" : "true");
    }
    if (industryField) {
      industryField.classList.toggle("post-master-field--disabled", !enabled);
      industryField.setAttribute("aria-disabled", enabled ? "false" : "true");
    }
  }

  function updateMasterLinks() {
    const customId = getSelectedGroupCustomId();
    // 投稿フォーム内にはマスタリンクを置かない方針（モーダル内にのみ表示）
    // ここは互換で残しているだけ
  }

  function clearSelect(selectEl) {
    // required想定なので未選択には戻さない（グループ変更時のみクリア）
    while (selectEl.options.length) selectEl.remove(0);
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "";
    selectEl.appendChild(opt);
    selectEl.value = "";
  }

  function ensureOption(selectEl, value, label) {
    const v = String(value);
    const exists = Array.from(selectEl.options).some((o) => String(o.value) === v);
    if (!exists) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = label;
      selectEl.appendChild(opt);
    }
    selectEl.value = v;
  }

  async function fetchMasters(kind, q) {
    const customId = getSelectedGroupCustomId();
    if (!customId) return { results: [] };
    const base =
      kind === "product"
        ? `/mysfa/group/${encodeURIComponent(customId)}/api/product-masters/`
        : `/mysfa/group/${encodeURIComponent(customId)}/api/industry-masters/`;

    const url = new URL(base, window.location.origin);
    if (q) url.searchParams.set("q", q);
    url.searchParams.set("limit", "50");

    const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
    if (!res.ok) return { results: [] };
    return await res.json();
  }

  function setChip(kind, label) {
    const el = kind === "product" ? productSelected : industrySelected;
    el.innerHTML = "";

    const span = document.createElement("span");
    span.className = "post-master-chip__label";
    span.textContent = label;
    el.appendChild(span);
    el.style.display = "inline-flex";
    // 操作ボタンは1つにする（openボタン側を「変更」に）
    if (kind === "product") productOpen.textContent = "変更";
    if (kind === "industry") industryOpen.textContent = "変更";
  }

  function applySelection(kind, id, label) {
    if (kind === "product") {
      // submit用 select の表示ラベルは自由。検索結果はコード+名前でも良いが、
      // UIチップは「商品名のみ」に寄せる。
      ensureOption(productSelect, id, label);
      setChip("product", label);
    } else {
      ensureOption(industrySelect, id, label);
      setChip("industry", label);
    }
    closeModal();
  }

  function openModal(nextMode) {
    const customId = getSelectedGroupCustomId();
    if (!customId) return;
    mode = nextMode;

    modalTitle.textContent = mode === "product" ? "商品を検索して選択" : "業態を検索して選択";
    modalSearch.value = "";
    modalSearch.placeholder = mode === "product" ? "商品コード / 商品名で検索" : "業態名で検索";

    modalMasterLink.href =
      mode === "product"
        ? `/mysfa/group/${encodeURIComponent(customId)}/product-master/`
        : `/mysfa/group/${encodeURIComponent(customId)}/industry-master/`;

    modalResults.innerHTML = "";
    modalEmpty.style.display = "none";

    overlay.classList.add("is-open");
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    modalSearch.focus();

    loadModalResults("");
  }

  function closeModal() {
    overlay.classList.remove("is-open");
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    mode = null;
  }

  async function loadModalResults(q) {
    if (!mode) return;
    const data = await fetchMasters(mode, q);
    const items = Array.isArray(data.results) ? data.results : [];

    modalResults.innerHTML = "";
    if (!items.length) {
      modalEmpty.style.display = "block";
      return;
    }
    modalEmpty.style.display = "none";

    for (const it of items) {
      const li = document.createElement("li");
      li.className = "post-master-result";
      li.innerHTML = `<button type="button" class="post-master-result-btn" data-id="${escapeHtml(
        it.id
      )}" data-label="${escapeHtml(it.label)}" data-name="${escapeHtml(
        it.name ?? ""
      )}">${escapeHtml(it.label)}</button>`;
      modalResults.appendChild(li);
    }
  }

  const debouncedModal = debounce((q) => loadModalResults(q), 250);

  function clearSelectionsForGroupChange() {
    clearSelect(productSelect);
    clearSelect(industrySelect);
    productSelected.style.display = "none";
    industrySelected.style.display = "none";
    productOpen.textContent = "商品を選択";
    industryOpen.textContent = "業態を選択";
  }

  // 初期化
  updateMasterLinks();
  setEnabledForMasters(Boolean(getSelectedGroupCustomId()));

  groupSelect.addEventListener("change", () => {
    updateMasterLinks();
    const enabled = Boolean(getSelectedGroupCustomId());
    setEnabledForMasters(enabled);
    clearSelectionsForGroupChange();
  });

  productOpen.addEventListener("click", () => openModal("product"));
  industryOpen.addEventListener("click", () => openModal("industry"));

  modalClose.addEventListener("click", closeModal);
  overlay.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  modalSearch.addEventListener("input", () => {
    if (!mode) return;
    debouncedModal(modalSearch.value.trim());
  });

  modalResults.addEventListener("click", (e) => {
    const btn = e.target?.closest?.(".post-master-result-btn");
    if (!btn || !mode) return;
    const id = btn.getAttribute("data-id");
    const label = btn.getAttribute("data-label") || "";
    const name = btn.getAttribute("data-name") || "";
    if (!id) return;

    // チップ表示は「商品名のみ」(業態は元々 name=label)
    if (mode === "product") {
      const productName =
        name ||
        (label ? label.replace(/^\S+\s+/, "") : "");
      applySelection("product", id, productName || label);
      return;
    }

    applySelection("industry", id, name || label);
  });
});

