let productChart = null;
let customerChart = null;

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

  const url = `/mysfa/sales-report-data/?start_date=${encodeURIComponent(
    startDate
  )}&end_date=${encodeURIComponent(endDate)}`;

  fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      return response.json();
    })
    .then((data) => {
      if (!data || data.error) return;
      if (!data.labels || !data.values) return;
      updateCharts(data);
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
