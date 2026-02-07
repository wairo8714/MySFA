document.addEventListener("DOMContentLoaded", () => {
  const groupSelect = document.getElementById("group");
  const mainSelect = document.getElementById("category_main");
  const subSelect = document.getElementById("category_sub");
  if (!groupSelect || !mainSelect || !subSelect) return;

  function setOptions(selectEl, items, selectedValue) {
    const keep = String(selectedValue || "");
    while (selectEl.options.length) selectEl.remove(0);
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "全て";
    selectEl.appendChild(opt0);
    for (const v of items || []) {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      selectEl.appendChild(opt);
    }
    if (keep && Array.from(selectEl.options).some((o) => o.value === keep)) {
      selectEl.value = keep;
    } else {
      selectEl.value = "";
    }
  }

  async function load(customId) {
    const url = `/mysfa/group/${encodeURIComponent(customId)}/api/product-categories/`;
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!res.ok) return { category_main: [], category_sub: [] };
    const data = await res.json();
    return {
      category_main: Array.isArray(data.category_main) ? data.category_main : [],
      category_sub: Array.isArray(data.category_sub) ? data.category_sub : [],
    };
  }

  let lastGroup = String(groupSelect.value || "");

  async function refresh(isInitial) {
    const customId = String(groupSelect.value || "");
    if (!customId) {
      mainSelect.disabled = true;
      subSelect.disabled = true;
      setOptions(mainSelect, [], "");
      setOptions(subSelect, [], "");
      lastGroup = "";
      return;
    }

    const selectedMain = isInitial
      ? mainSelect.getAttribute("data-selected")
      : lastGroup === customId
        ? mainSelect.value
        : "";
    const selectedSub = isInitial
      ? subSelect.getAttribute("data-selected")
      : lastGroup === customId
        ? subSelect.value
        : "";

    mainSelect.disabled = false;
    subSelect.disabled = false;

    const data = await load(customId);
    setOptions(mainSelect, data.category_main, selectedMain);
    setOptions(subSelect, data.category_sub, selectedSub);
    lastGroup = customId;
  }

  refresh(true);
  groupSelect.addEventListener("change", () => refresh(false));
});

