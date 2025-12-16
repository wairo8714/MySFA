document.addEventListener('DOMContentLoaded', function() {
    const menuOpen = document.querySelector('#humburger-icon');
    const menuClose = document.querySelector('.overlay');
    const sidebar = document.querySelector('.sidebar-inner');
    const overlay = document.querySelector('.overlay');
    const menuOptions = {
        duration: 700,
        easing: 'ease',
        fill: 'forwards',
    };

    if (sidebar && overlay) {
        sidebar.style.transition = `transform ${menuOptions.duration}ms ${menuOptions.easing} ${menuOptions.fill}`;
        overlay.style.transition = `background-color ${menuOptions.duration}ms ${menuOptions.easing}`;
    }

    if (menuOpen) {
        menuOpen.addEventListener('click', () => {
            if (sidebar) {
                sidebar.style.transform = 'translateX(0)';
            }
            if (overlay) {
                overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
                overlay.style.display = 'block';
            }
        });
    }

    if (menuClose) {
        menuClose.addEventListener('click', () => {
            if (sidebar) {
                sidebar.style.transform = 'translateX(100%)';
            }
            if (overlay) {
                overlay.style.backgroundColor = 'rgba(0, 0, 0, 0)';
                setTimeout(() => {
                    overlay.style.display = 'none';
                }, menuOptions.duration);
            }
        });
    }

    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const dropdownMenu = this.nextElementSibling;
            const dropdownArrow = this.querySelector('.dropdown-arrow');

            if (dropdownMenu) {
                dropdownMenu.classList.toggle('show');
            }
            if (dropdownArrow) {
                dropdownArrow.classList.toggle('rotate');
            }
        });
    });

    document.addEventListener('click', function(event) {
        dropdownToggles.forEach(toggle => {
            const dropdownMenu = toggle.nextElementSibling;
            const dropdownArrow = toggle.querySelector('.dropdown-arrow');

            if (dropdownMenu && dropdownMenu.classList.contains('show') && !toggle.contains(event.target) && !dropdownMenu.contains(event.target)) {
                dropdownMenu.classList.remove('show');
                if (dropdownArrow) {
                    dropdownArrow.classList.remove('rotate');
                }
            }
        });
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const postModal = document.getElementById('postModal');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');

    if (openModalBtn) {
        openModalBtn.addEventListener('click', function() {
            if (postModal) postModal.style.display = 'block';
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function() {
            if (postModal) postModal.style.display = 'none';
        });
    }

    window.addEventListener('click', function(event) {
        if (event.target === postModal) {
            postModal.style.display = 'none';
        }
    });
});

function toggleAccordion(accordionId) {
    const accordion = document.getElementById(accordionId);
    const icon = document.getElementById(accordionId.replace('accordion', 'icon'));

    if (accordion && icon) {
        if (accordion.style.display === "none" || accordion.style.display === "") {
            accordion.style.display = "block";
            icon.textContent = "-";
        } else {
            accordion.style.display = "none";
            icon.textContent = "+";
        }
    }
}

// 同一商品に対する複数の顧客情報を表示
function showCustomers(productId) {
    const customers = document.getElementById(`customers-${productId}`);
    if (customers) {
        if (customers.classList.contains("show")) {
            customers.classList.remove("show");
        } else {
            customers.classList.add("show");
        }
    }
}

// 顧客情報の詳細を表示
function showCustomerDetails(customerId) {
    const details = document.getElementById(`details-${customerId}`);
    if (details) {
        if (details.classList.contains("show")) {
            details.classList.remove("show");
        } else {
            details.classList.add("show");
        }
    }
}

// ページ遷移時のメッセージ表示（例）
document.addEventListener('DOMContentLoaded', function() {
    const messageElement = document.querySelector('.message');
    if (messageElement) {
        setTimeout(() => {
            messageElement.style.opacity = '0';
        }, 3000);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const scrollToTopBtn = document.getElementById("scrollToTopBtn");
    if (!scrollToTopBtn) return;

    window.onscroll = function() { scrollFunction() };

    function scrollFunction() {
        if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
            scrollToTopBtn.style.display = "block";
        } else {
            scrollToTopBtn.style.display = "none";
        }
    }

    scrollToTopBtn.addEventListener('click', function() {
        document.body.scrollTop = 0;
        document.documentElement.scrollTop = 0;
    });
});

// =========================
// Like Feature (Demo-safe)
// =========================

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== LIKE FUNCTION LOADED ===');

    const likeButtons = document.querySelectorAll('.like-button');
    console.log('Found like buttons:', likeButtons.length);

    if (likeButtons.length === 0) {
        console.log('No like buttons found!');
        return;
    }

    const csrfInput = document.querySelector('input[name=csrfmiddlewaretoken]');
    if (!csrfInput) {
        console.warn('CSRF token not found. Like feature disabled.');
        return;
    }
    const csrfToken = csrfInput.value;

    likeButtons.forEach((button, index) => {
        console.log(`Button ${index}:`, button);

        button.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Like button clicked!');

            const postId = this.dataset.postId;
            const likeCount = this.querySelector('.like-count');

            console.log('Post ID:', postId);
            console.log('Current count:', likeCount.textContent);

            console.log('CSRF Token:', csrfToken ? 'Found' : 'Not found');

            const url = `/mysfa/like-post/${postId}/`;
            console.log('Request URL:', url);

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);

                // ★追加：デモ時に Middleware が 401 + {redirect: "..."} を返したらログインへ
                if (response.status === 401) {
                    return response.json().then(data => {
                        window.location.href = data.redirect;
                        return null; // 次の then に渡さない
                    });
                }

                return response.json();
            })
            .then(data => {
                if (!data) return;

                console.log('Response data:', data);
                if (data.status === 'liked' || data.status === 'unliked') {
                    likeCount.textContent = data.count;
                    console.log('Count updated to:', data.count);

                    if (data.status === 'liked') {
                        button.classList.add('liked');
                    } else {
                        button.classList.remove('liked');
                    }
                } else {
                    console.error('Error in response:', data.message);
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
            });
        });
    });
});

let productChart = null;
let customerChart = null;

function initializeSalesReport() {
    console.log('=== INITIALIZING SALES REPORT ===');

    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (!startDateInput || !endDateInput) {
        console.error('Date inputs not found!');
        return;
    }

    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 1);

    startDateInput.value = startDate.toISOString().split('T')[0];
    endDateInput.value = endDate.toISOString().split('T')[0];

    console.log('Default date range set:', startDateInput.value, 'to', endDateInput.value);

    loadSalesReport();

    const updateButton = document.getElementById('update-report');
    if (updateButton) {
        updateButton.addEventListener('click', function() {
            console.log('Update button clicked');
            loadSalesReport();
        });
    }
}

function loadSalesReport() {
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;

    if (!startDate || !endDate) {
        console.error('Start or end date not provided');
        return;
    }

    console.log('Loading report for date range:', startDate, 'to', endDate);

    const url = `/mysfa/sales-report-data/?start_date=${startDate}&end_date=${endDate}`;
    console.log('Fetching data from:', url);

    fetch(url)
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received data:', data);

            if (data.error) {
                console.error('Error from server:', data.error);
                return;
            }

            if (!data.labels || !data.values) {
                console.error('Invalid data format received');
                return;
            }

            updateCharts(data);
        })
        .catch(error => {
            console.error('Fetch error:', error);
        });
}

function updateCharts(data) {
    console.log('Updating charts with data:', data);

    const productChartCanvas = document.getElementById('product-chart');
    const customerChartCanvas = document.getElementById('customer-chart');

    if (!productChartCanvas || !customerChartCanvas) {
        console.error('Chart canvases not found');
        return;
    }

    const productCtx = productChartCanvas.getContext('2d');
    const customerCtx = customerChartCanvas.getContext('2d');

    if (productChart) {
        productChart.destroy();
    }
    if (customerChart) {
        customerChart.destroy();
    }

    productChart = new Chart(productCtx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: '商品別売上',
                data: data.values,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    customerChart = new Chart(customerCtx, {
        type: 'bar',
        data: {
            labels: data.customer_labels || [],
            datasets: [{
                label: '業態別売上',
                data: data.customer_values || [],
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    const chartsContainer = document.querySelector('.charts-container');
    if (chartsContainer) {
        chartsContainer.style.minHeight = '400px';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initializeSalesReport();
});
