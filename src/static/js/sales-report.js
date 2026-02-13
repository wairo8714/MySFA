let productChart = null;
let customerChart = null;

function makeSalesReportColors(labels) {
  const colors = [
    "#0B5FFF",
    "#1E88E5",
    "#1565C0",
    "#0D47A1",
    "#2F6FED",
    "#00A3FF",
    "#00B8D9",
    "#00BFA6",
    "#00C853",
    "#64DD17",
    "#FFD600",
    "#FFB300",
    "#FB8C00",
    "#F4511E",
    "#E53935",
    "#D81B60",
    "#8E24AA",
    "#5E35B1",
    "#3949AB",
    "#546E7A",
  ];
  const otherColor = "#94a3b8";
  return (labels || []).map((label, i) =>
    String(label || "") === "その他" ? otherColor : colors[i % colors.length]
  );
}

function getReportGroupCustomId() {
  const path = window.location.pathname || "";
  const m2 = path.match(/^\/mysfa\/group\/([^/]+)\/?/);
  if (m2 && m2[1]) return m2[1];

  const params = new URLSearchParams(window.location.search || "");
  const customId = params.get("custom_id");
  return customId || "";
}

function getSalesReportEmptyImageUrl() {
  const el = document.querySelector(".sales-report-assets[data-sales-report-empty-image]");
  const url = el?.getAttribute?.("data-sales-report-empty-image");
  return url || "/static/images/error.png";
}

function getReportSortKey() {
  const select = document.getElementById("report-sort");
  const value = String(select?.value || "").trim();
  if (value) return value;
  const params = new URLSearchParams(window.location.search || "");
  return String(params.get("report_sort") || "").trim();
}

function getReportStatusKey() {
  const select = document.getElementById("report-status");
  const value = String(select?.value || "").trim();
  if (value) return value;
  const params = new URLSearchParams(window.location.search || "");
  return String(params.get("report_status") || "").trim();
}

function getReportTopNKey() {
  const select = document.getElementById("report-top-n");
  const value = String(select?.value || "").trim();
  if (value) return value;
  const params = new URLSearchParams(window.location.search || "");
  return String(params.get("report_top_n") || "").trim();
}

function syncReportControlsToUrl() {
  const params = new URLSearchParams(window.location.search || "");
  const sortEl = document.getElementById("report-sort");
  const statusEl = document.getElementById("report-status");
  const topNEl = document.getElementById("report-top-n");

  const sortV = String(sortEl?.value || "").trim();
  if (sortV) params.set("report_sort", sortV);
  else params.delete("report_sort");

  const statusV = String(statusEl?.value || "").trim();
  if (statusV) params.set("report_status", statusV);
  else params.delete("report_status");

  const topNV = String(topNEl?.value || "").trim();
  if (topNV) params.set("report_top_n", topNV);
  else params.delete("report_top_n");

  const qs = params.toString();
  const newUrl = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
  window.history.replaceState({}, "", newUrl);
}

function setSalesReportEmptyMessage(show) {
  const container = document.querySelector(".sales-report-section");
  if (!container) return;

  const chartsContainer = container.querySelector(".charts-container");

  const id = "sales-report-empty-message";
  let el = document.getElementById(id);

  if (!show) {
    if (el) el.remove();
    container.classList.remove("is-empty");
    if (chartsContainer) {
      chartsContainer.style.display = "";
    }
    return;
  }

  container.classList.add("is-empty");
  if (chartsContainer) {
    chartsContainer.style.display = "none";
    chartsContainer.style.minHeight = "";
  }

  if (!el) {
    el = document.createElement("div");
    el.id = id;
    el.className = "sales-report-empty";

    const img = document.createElement("img");
    img.className = "sales-report-empty__img";
    img.alt = "";
    img.src = getSalesReportEmptyImageUrl();

    const p = document.createElement("p");
    p.className = "sales-report-empty__text";
    p.textContent = "該当するデータが見つかりませんでした。";

    el.appendChild(img);
    el.appendChild(p);
    container.appendChild(el);
  }
}

function clearCharts() {
  if (productChart) {
    productChart.destroy();
    productChart = null;
  }
  if (customerChart) {
    customerChart.destroy();
    customerChart = null;
  }
}

function renderDetailsLists(productData, productOther, customerData, customerOther, normalized) {
  const groupCustomId = getReportGroupCustomId();

  const productWrapper = document.getElementById("product-chart")?.closest(".chart-wrapper");
  const customerWrapper = document.getElementById("customer-chart")?.closest(".chart-wrapper");

  const cleanupOld = (wrapper, kind) => {
    if (!wrapper) return;
    const oldIds = [
      `sales-report-breakdown-${kind}`,
      `sales-report-toplist-${kind}`,
    ];
    oldIds.forEach((id) => {
      const el = wrapper.querySelector(`#${id}`);
      if (el) el.remove();
    });
  };

  const ensureDetails = (wrapper, kind) => {
    if (!wrapper) return null;
    const id = `sales-report-toplist-${kind}`;
    let el = wrapper.querySelector(`#${id}`);
    if (!el) {
      el = document.createElement("details");
      el.id = id;
      el.className = "sales-report-breakdown sales-report-breakdown--toplist";
      el.open = false;

      const summary = document.createElement("summary");
      summary.className = "sales-report-breakdown__summary";
      summary.textContent = "内訳";
      el.appendChild(summary);

      const ul = document.createElement("ul");
      ul.className = "sales-report-breakdown__list";
      el.appendChild(ul);

      wrapper.appendChild(el);
    }
    return el;
  };

  const renderList = (detailsEl, items, makeRow) => {
    if (!detailsEl) return;
    const ul = detailsEl.querySelector(".sales-report-breakdown__list");
    const summary = detailsEl.querySelector(".sales-report-breakdown__summary");
    if (!ul || !summary) return;

    ul.innerHTML = "";

    if (!items || !items.length) {
      detailsEl.style.display = "none";
      return;
    }

    detailsEl.style.display = "";
    summary.textContent = detailsEl.dataset.summary || "内訳";

    items.forEach((x, i) => {
      const li = makeRow(x, i);
      if (li) ul.appendChild(li);
    });
  };

  const normalizeProductName = (s) => {
    const raw = String(s || "").trim();
    if (!raw) return "";
    const m = raw.match(/^([A-Za-z0-9_-]{1,20})\s+(.+)$/);
    if (m && m[2]) return String(m[2]).trim();
    return raw;
  };

  const productTopItems = (Array.isArray(productData) ? productData : []).filter(
    (x) => String(x?.label || x?.product_name || "") !== "その他"
  );
  const customerTopItems = (Array.isArray(customerData) ? customerData : []).filter(
    (x) => String(x?.customer_category || "") !== "その他"
  );

  const productItems = [...productTopItems, ...(Array.isArray(productOther) ? productOther : [])];
  const customerItems = [...customerTopItems, ...(Array.isArray(customerOther) ? customerOther : [])];

  const productColors = makeSalesReportColors(productItems.map((x) => x?.label || x?.product_name || x?.product_code || ""));
  const customerColors = makeSalesReportColors(customerItems.map((x) => x?.customer_category || ""));

  cleanupOld(productWrapper, "product");
  cleanupOld(customerWrapper, "customer");

  const productDetails = ensureDetails(productWrapper, "product");
  if (productDetails) {
    productDetails.dataset.summary = `内訳（表示${productTopItems.length}件/その他${(Array.isArray(productOther) ? productOther : []).length}件）`;
  }
  renderList(productDetails, productItems, (x, i) => {
    const name = String(x?.product_name || x?.label || "").trim();
    const code = String(x?.product_code || "").trim();
    const count = Number(x?.count) || 0;
    if (!name) return null;

    const label = normalizeProductName(code ? `${code} ${name}` : name);
    const isOtherBucket = i >= productTopItems.length;

    const li = document.createElement("li");
    li.className = "sales-report-breakdown__item";

    const left = document.createElement("a");
    left.className = "sales-report-breakdown__left sales-report-breakdown__name-link";

    const swatch = document.createElement("span");
    swatch.className = "sales-report-breakdown__swatch";
    swatch.style.backgroundColor = productColors[i] || "#94a3b8";

    const text = document.createElement("span");
    text.textContent = label;

    left.appendChild(swatch);
    left.appendChild(text);

    const q = (code || name).trim();
    const params = new URLSearchParams();
    params.set("q", q);
    params.set("match", "exact");
    if (groupCustomId) params.set("group", groupCustomId);
    left.href = `/mysfa/search_products/?${params.toString()}`;

    const right = document.createElement("div");
    right.className = "sales-report-breakdown__right";

    if (isOtherBucket) {
      const tag = document.createElement("span");
      tag.className = "sales-report-breakdown__tag";
      tag.textContent = "その他";
      right.appendChild(tag);
    }

    const badge = document.createElement("span");
    badge.className = "sales-report-breakdown__count";
    badge.textContent = String(count);
    right.appendChild(badge);

    li.appendChild(left);
    li.appendChild(right);
    return li;
  });

  const customerDetails = ensureDetails(customerWrapper, "customer");
  if (customerDetails) {
    customerDetails.dataset.summary = `内訳（表示${customerTopItems.length}件/その他${(Array.isArray(customerOther) ? customerOther : []).length}件）`;
  }
  renderList(customerDetails, customerItems, (x, i) => {
    const name = String(x?.customer_category || "").trim();
    const count = Number(x?.count) || 0;
    if (!name) return null;
    const isOtherBucket = i >= customerTopItems.length;

    const li = document.createElement("li");
    li.className = "sales-report-breakdown__item";

    const left = document.createElement("a");
    left.className = "sales-report-breakdown__left sales-report-breakdown__name-link";

    const swatch = document.createElement("span");
    swatch.className = "sales-report-breakdown__swatch";
    swatch.style.backgroundColor = customerColors[i] || "#94a3b8";

    const text = document.createElement("span");
    text.textContent = name;

    left.appendChild(swatch);
    left.appendChild(text);

    const right = document.createElement("div");
    right.className = "sales-report-breakdown__right";

    if (isOtherBucket) {
      const tag = document.createElement("span");
      tag.className = "sales-report-breakdown__tag";
      tag.textContent = "その他";
      right.appendChild(tag);
    }

    const badge = document.createElement("span");
    badge.className = "sales-report-breakdown__count";
    badge.textContent = String(count);
    right.appendChild(badge);

    const params = new URLSearchParams();
    params.set("q", name);
    params.set("match", "exact");
    if (groupCustomId) params.set("group", groupCustomId);
    left.href = `/mysfa/search_customers/?${params.toString()}`;

    li.appendChild(left);
    li.appendChild(right);
    return li;
  });
}

function getSalesReportUrl(startDate, endDate) {
  const path = window.location.pathname || "";
  const params = new URLSearchParams(window.location.search || "");
  const selectedGroupCustomId = params.get("custom_id") || "";
  const reportSort = getReportSortKey();
  const reportStatus = getReportStatusKey();
  const reportTopN = getReportTopNKey();

  const m1 = path.match(/^\/mysfa\/mypost\/([^/]+)\/?/);
  if (m1 && m1[1]) {
    return `/mysfa/sales-report/${encodeURIComponent(m1[1])}/?start_date=${encodeURIComponent(
      startDate
    )}&end_date=${encodeURIComponent(endDate)}${
      selectedGroupCustomId ? `&custom_id=${encodeURIComponent(selectedGroupCustomId)}` : ""
    }${reportStatus ? `&report_status=${encodeURIComponent(reportStatus)}` : ""}${reportSort ? `&report_sort=${encodeURIComponent(reportSort)}` : ""}${reportTopN ? `&report_top_n=${encodeURIComponent(reportTopN)}` : ""}`;
  }

  const m2 = path.match(/^\/mysfa\/group\/([^/]+)\/?/);
  if (m2 && m2[1]) {
    return `/mysfa/sales-report/group/${encodeURIComponent(
      m2[1]
    )}/?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(
      endDate
    )}${reportStatus ? `&report_status=${encodeURIComponent(reportStatus)}` : ""}${reportSort ? `&report_sort=${encodeURIComponent(reportSort)}` : ""}${reportTopN ? `&report_top_n=${encodeURIComponent(reportTopN)}` : ""}`;
  }

  return `/mysfa/sales-report/?start_date=${encodeURIComponent(
    startDate
  )}&end_date=${encodeURIComponent(endDate)}${reportStatus ? `&report_status=${encodeURIComponent(reportStatus)}` : ""}${reportSort ? `&report_sort=${encodeURIComponent(reportSort)}` : ""}${reportTopN ? `&report_top_n=${encodeURIComponent(reportTopN)}` : ""}`;
}

function initializeSalesReport() {
  const startDateInput = document.getElementById("start-date");
  const endDateInput = document.getElementById("end-date");
  if (!startDateInput || !endDateInput) return;

  const reportSortSelect = document.getElementById("report-sort");
  if (reportSortSelect) {
    const params = new URLSearchParams(window.location.search || "");
    const v = String(params.get("report_sort") || "").trim();
    if (v) reportSortSelect.value = v;
    reportSortSelect.addEventListener("change", function () {
      syncReportControlsToUrl();
      loadSalesReport();
    });
  }

  const reportStatusSelect = document.getElementById("report-status");
  if (reportStatusSelect) {
    const params = new URLSearchParams(window.location.search || "");
    const v = String(params.get("report_status") || "").trim();
    if (v) reportStatusSelect.value = v;
    reportStatusSelect.addEventListener("change", function () {
      syncReportControlsToUrl();
      loadSalesReport();
    });
  }

  const reportTopNSelect = document.getElementById("report-top-n");
  if (reportTopNSelect) {
    const params = new URLSearchParams(window.location.search || "");
    const v = String(params.get("report_top_n") || "").trim();
    if (v) reportTopNSelect.value = v;
    reportTopNSelect.addEventListener("change", function () {
      syncReportControlsToUrl();
      loadSalesReport();
    });
  }

  const endDate = new Date();
  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 1);

  startDateInput.value = startDate.toISOString().split("T")[0];
  endDateInput.value = endDate.toISOString().split("T")[0];

  loadSalesReport();

  const updateButton = document.getElementById("update-report");
  if (updateButton) {
    updateButton.addEventListener("click", function () {
      syncReportControlsToUrl();
      loadSalesReport();
    });
  }
}

function loadSalesReport() {
  const startDate = document.getElementById("start-date")?.value;
  const endDate = document.getElementById("end-date")?.value;
  if (!startDate || !endDate) return;

  const rawUrl = getSalesReportUrl(startDate, endDate);
  const urlObj = new URL(rawUrl, window.location.origin);
  urlObj.searchParams.set("_", String(Date.now()));
  const url = urlObj.toString();

  fetch(url, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (!data || data.error) return;

      const productData = Array.isArray(data.product_data) ? data.product_data : [];
      const customerData = Array.isArray(data.customer_data) ? data.customer_data : [];
      const productOther = Array.isArray(data.product_other_breakdown)
        ? data.product_other_breakdown
        : [];
      const customerOther = Array.isArray(data.customer_other_breakdown)
        ? data.customer_other_breakdown
        : [];

      const normalizeProductName = (s) => {
        const raw = String(s || "").trim();
        if (!raw) return "";
        const m = raw.match(/^([A-Za-z0-9_-]{1,20})\s+(.+)$/);
        if (m && m[2]) return String(m[2]).trim();
        return raw;
      };

      const normalized = {
        labels: productData.map((x) =>
          normalizeProductName(x?.label || x?.product_name || x?.product_code || "")
        ),
        values: productData.map((x) => x.count),
        customer_labels: customerData.map((x) => x.customer_category),
        customer_values: customerData.map((x) => x.count),
      };

      if (!normalized.labels.length && !normalized.customer_labels.length) {
        clearCharts();
        renderDetailsLists([], [], [], [], { labels: [], customer_labels: [] });
        setSalesReportEmptyMessage(true);
        return;
      }

      setSalesReportEmptyMessage(false);
      updateCharts(normalized);
      renderDetailsLists(productData, productOther, customerData, customerOther, normalized);
    })
    .catch(() => {});
}

function updateCharts(data) {
  const productChartCanvas = document.getElementById("product-chart");
  const customerChartCanvas = document.getElementById("customer-chart");
  if (!productChartCanvas || !customerChartCanvas) return;

  if (typeof Chart === "undefined") return;

  const productCtx = productChartCanvas.getContext("2d");
  const customerCtx = customerChartCanvas.getContext("2d");
  if (!productCtx || !customerCtx) return;

  if (productChart) productChart.destroy();
  if (customerChart) customerChart.destroy();

  productChart = new Chart(productCtx, {
    type: "pie",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "商品別売上",
          data: data.values,
          backgroundColor: makeSalesReportColors(data.labels || []),
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
    },
  });

  customerChart = new Chart(customerCtx, {
    type: "pie",
    data: {
      labels: data.customer_labels || [],
      datasets: [
        {
          label: "業態別売上",
          data: data.customer_values || [],
          backgroundColor: makeSalesReportColors(data.customer_labels || []),
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
    },
  });

  const chartsContainer = document.querySelector(".charts-container");
  if (chartsContainer) chartsContainer.style.display = "";
  const section = document.querySelector(".sales-report-section");
  if (section) section.classList.remove("is-empty");
}

document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("start-date") && document.getElementById("end-date")) {
    initializeSalesReport();
  }
});
