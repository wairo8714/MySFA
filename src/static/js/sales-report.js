let productChart = null;
let customerChart = null;

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

  const m1 = path.match(/^\/mysfa\/mypost\/([^/]+)\/?/);
  if (m1 && m1[1]) {
    return `/mysfa/sales-report/${encodeURIComponent(m1[1])}/?start_date=${encodeURIComponent(
      startDate
    )}&end_date=${encodeURIComponent(endDate)}`;
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
        setSalesReportEmptyMessage(true);
        return;
      }

      setSalesReportEmptyMessage(false);
      updateCharts(normalized);
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
  const makeColors = (n) => {
    const base = colors.slice(0, Math.max(0, n));
    if (base.length >= n) return base;
    return base.concat(Array.from({ length: n - base.length }, () => colors[colors.length - 1]));
  };

  // 商品別
  productChart = new Chart(productCtx, {
    type: "pie",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "商品別売上",
          data: data.values,
          backgroundColor: makeColors((data.labels || []).length),
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
          backgroundColor: makeColors((data.customer_labels || []).length),
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

document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("start-date") && document.getElementById("end-date")) {
    initializeSalesReport();
  }
});
