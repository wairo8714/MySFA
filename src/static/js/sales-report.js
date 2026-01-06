let productChart = null;
let customerChart = null;

function setSalesReportEmptyMessage(show) {
  const container = document.querySelector(".sales-report-section");
  if (!container) return;

  const id = "sales-report-empty-message";
  let el = document.getElementById(id);

  if (!show) {
    if (el) el.remove();
    return;
  }

  if (!el) {
    el = document.createElement("p");
    el.id = id;
    el.textContent = "投稿がありません";
    el.style.textAlign = "center";
    el.style.color = "#666";
    el.style.marginTop = "10px";
    el.style.marginBottom = "0";
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

  const url = getSalesReportUrl(startDate, endDate);

  fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (!data || data.error) return;

      const productData = Array.isArray(data.product_data) ? data.product_data : [];
      const customerData = Array.isArray(data.customer_data) ? data.customer_data : [];

      const normalized = {
        labels: productData.map((x) => x.product_name),
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

  const colors = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
  ];
  const makeColors = (n) => Array.from({ length: n }, (_, i) => colors[i % colors.length]);

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
  if (chartsContainer) chartsContainer.style.minHeight = "400px";
}

document.addEventListener("DOMContentLoaded", function () {
  if (document.getElementById("start-date") && document.getElementById("end-date")) {
    initializeSalesReport();
  }
});
