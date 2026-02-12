let productChart = null;
let customerChart = null;

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

function getSalesReportUrl(startDate, endDate) {
  const path = window.location.pathname || "";
  const params = new URLSearchParams(window.location.search || "");
  const selectedGroupCustomId = params.get("custom_id") || "";

  const m1 = path.match(/^\/mysfa\/mypost\/([^/]+)\/?/);
  if (m1 && m1[1]) {
    return `/mysfa/sales-report/${encodeURIComponent(m1[1])}/?start_date=${encodeURIComponent(
      startDate
    )}&end_date=${encodeURIComponent(endDate)}${
      selectedGroupCustomId ? `&custom_id=${encodeURIComponent(selectedGroupCustomId)}` : ""
    }`;
  }

  const m2 = path.match(/^\/mysfa\/group\/([^/]+)\/?/);
  if (m2 && m2[1]) {
    return `/mysfa/sales-report/group/${encodeURIComponent(
      m2[1]
    )}/?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(
      endDate
    )}`;
  }

  return `/mysfa/sales-report/?start_date=${encodeURIComponent(
    startDate
  )}&end_date=${encodeURIComponent(endDate)}`;
}

function initializeSalesReport() {
  const startDateInput = document.getElementById("start-date");
  const endDateInput = document.getElementById("end-date");
  if (!startDateInput || !endDateInput) return;

  const endDate = new Date();
  const startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 1);

  startDateInput.value = startDate.toISOString().split("T")[0];
  endDateInput.value = endDate.toISOString().split("T")[0];

  loadSalesReport();

  const updateButton = document.getElementById("update-report");
  if (updateButton) {
    updateButton.addEventListener("click", function () {
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
        renderBreakdowns([], []);
        setSalesReportEmptyMessage(true);
        return;
      }

      setSalesReportEmptyMessage(false);
      updateCharts(normalized);
      renderBreakdowns(productOther, customerOther);
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

  const colors = ["#2FBFD6", "#18ABCC", "#1399CF", "#1081C7", "#084F8C"];
  const otherColor = "#94a3b8";
  const makeColorsForLabels = (labels) =>
    (labels || []).map((label, i) =>
      String(label || "") === "その他" ? otherColor : colors[i % colors.length]
    );

  // 商品別
  productChart = new Chart(productCtx, {
    type: "pie",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "商品別売上",
          data: data.values,
          backgroundColor: makeColorsForLabels(data.labels || []),
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: true }, 
      },
    },
  });

  // 業態別
  customerChart = new Chart(customerCtx, {
    type: "pie",
    data: {
      labels: data.customer_labels || [],
      datasets: [
        {
          label: "業態別売上",
          data: data.customer_values || [],
          backgroundColor: makeColorsForLabels(data.customer_labels || []),
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: true },
      },
    },
  });

  const chartsContainer = document.querySelector(".charts-container");
  if (chartsContainer) chartsContainer.style.display = "";
  const section = document.querySelector(".sales-report-section");
  if (section) section.classList.remove("is-empty");
}

function renderBreakdowns(productOther, customerOther) {
  const groupCustomId = getReportGroupCustomId();

  const ensureDetails = (wrapper, kind) => {
    if (!wrapper) return null;
    const id = `sales-report-breakdown-${kind}`;
    let el = wrapper.querySelector(`#${id}`);
    if (!el) {
      el = document.createElement("details");
      el.id = id;
      el.className = "sales-report-breakdown";
      el.open = false;

      const summary = document.createElement("summary");
      summary.className = "sales-report-breakdown__summary";
      summary.textContent = "その他の内訳";
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
    const total = items.reduce((acc, x) => acc + (Number(x?.count) || 0), 0);
    summary.textContent = `その他の内訳（${items.length}件 / 合計${total}）`;

    items.forEach((x) => {
      const li = makeRow(x);
      if (li) ul.appendChild(li);
    });
  };

  const productWrapper = document.getElementById("product-chart")?.closest(".chart-wrapper");
  const customerWrapper = document.getElementById("customer-chart")?.closest(".chart-wrapper");

  const productDetails = ensureDetails(productWrapper, "product");
  renderList(productDetails, productOther, (x) => {
    const name = String(x?.product_name || x?.label || "").trim();
    const code = String(x?.product_code || "").trim();
    const count = Number(x?.count) || 0;
    if (!name) return null;

    const q = (code ? `${code} ${name}` : name).trim();
    const params = new URLSearchParams();
    params.set("q", q);
    params.set("match", "exact");
    if (groupCustomId) params.set("group", groupCustomId);

    const li = document.createElement("li");
    li.className = "sales-report-breakdown__item";

    const left = document.createElement("div");
    left.className = "sales-report-breakdown__left";
    left.textContent = code ? `${code} ${name}` : name;

    const right = document.createElement("div");
    right.className = "sales-report-breakdown__right";

    const badge = document.createElement("span");
    badge.className = "sales-report-breakdown__count";
    badge.textContent = String(count);

    const link = document.createElement("a");
    link.className = "sales-report-breakdown__link";
    link.href = `/mysfa/search_products/?${params.toString()}`;
    link.textContent = "見る";

    right.appendChild(badge);
    right.appendChild(link);

    li.appendChild(left);
    li.appendChild(right);
    return li;
  });

  const customerDetails = ensureDetails(customerWrapper, "customer");
  renderList(customerDetails, customerOther, (x) => {
    const name = String(x?.customer_category || "").trim();
    const count = Number(x?.count) || 0;
    if (!name) return null;

    const params = new URLSearchParams();
    params.set("q", name);
    params.set("match", "exact");
    if (groupCustomId) params.set("group", groupCustomId);

    const li = document.createElement("li");
    li.className = "sales-report-breakdown__item";

    const left = document.createElement("div");
    left.className = "sales-report-breakdown__left";
    left.textContent = name;

    const right = document.createElement("div");
    right.className = "sales-report-breakdown__right";

    const badge = document.createElement("span");
    badge.className = "sales-report-breakdown__count";
    badge.textContent = String(count);

    const link = document.createElement("a");
    link.className = "sales-report-breakdown__link";
    link.href = `/mysfa/search_customers/?${params.toString()}`;
    link.textContent = "見る";

    right.appendChild(badge);
    right.appendChild(link);

    li.appendChild(left);
    li.appendChild(right);
    return li;
  });
}

document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("start-date") && document.getElementById("end-date")) {
    initializeSalesReport();
  }
});
