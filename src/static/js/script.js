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
            setTimeout(() => {
                if (overlay) {
                    overlay.style.display = 'block';
                    requestAnimationFrame(() => {
                        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
                    });
                }
            }, 100);
        });
    }

    if (menuClose) {
        menuClose.addEventListener('click', () => {
            if (sidebar) {
                sidebar.style.transform = 'translateX(100vw)';
            }
            if (overlay) {
                overlay.style.display = 'none';
            }
        });
    }

    const form = document.querySelector('.signup-input-area');
    if (form) {
        form.addEventListener('submit', function(event) {
            const password1 = document.getElementById('registeringPassword1').value;
            const password2 = document.getElementById('registeringPassword2').value;
            const userID = document.getElementById('registeringUserID').value;

            if (password1 !== password2) {
                event.preventDefault();
                alert('パスワードが一致しません。');
                return;
            }

            fetch(`/accounts/check_user_id/?custom_user_id=${encodeURIComponent(userID)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.exists) {
                        event.preventDefault();
                        alert('このユーザーIDはすでに別のユーザーによって使用されています。');
                    } else {
                        form.submit();
                    }
                })
                .catch(error => {
                    event.preventDefault();
                    console.error('Error:', error);
                    alert('ユーザーIDの確認中にエラーが発生しました。');
                });

            event.preventDefault();
        });
    }

    function checkUserId() {
        const userId = document.getElementById('registeringUserID').value;
        fetch(`/accounts/check_user_id/?custom_user_id=${userId}`)
            .then(response => response.json())
            .then(data => {
                const messageElement = document.getElementById('user-id-message');
                if (data.error) {
                    messageElement.textContent = data.error;
                    messageElement.style.color = 'red';
                } else {
                    messageElement.textContent = data.success;
                    messageElement.style.color = 'green';
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    const userIdInput = document.getElementById('registeringUserID');
    if (userIdInput) {
        userIdInput.addEventListener('blur', checkUserId);
    }

    const productSearchButton = document.getElementById('product-search');
    const productSearchModal = document.getElementById('product-search-modal');
    if (productSearchButton && productSearchModal) {
        productSearchButton.addEventListener('click', function(event) {
            event.preventDefault();
            productSearchModal.style.display = 'block';
        });

        document.addEventListener('click', function(event) {
            if (event.target !== productSearchModal && !productSearchModal.contains(event.target) && event.target !== productSearchButton) {
                productSearchModal.style.display = 'none';
            }
        });
    }

    const customerCategorySearchButton = document.getElementById('customer-category-search');
    const customerCategorySearchModal = document.getElementById('customer-category-search-modal');
    if (customerCategorySearchButton && customerCategorySearchModal) {
        customerCategorySearchButton.addEventListener('click', function(event) {
            event.preventDefault();
            customerCategorySearchModal.style.display = 'block';
        });

        document.addEventListener('click', function(event) {
            if (event.target !== customerCategorySearchModal && !customerCategorySearchModal.contains(event.target) && event.target !== customerCategorySearchButton) {
                customerCategorySearchModal.style.display = 'none';
            }
        });
    }

    const textarea = document.querySelector('#id_contents');
    const charCounter = document.querySelector('#char-counter');
    const maxChars = 100;

    textarea.addEventListener('input', function() {
        const currentLength = textarea.value.length;
        charCounter.textContent = `${currentLength}/${maxChars}`;

        if (currentLength >= maxChars) {
            charCounter.style.color = 'red';
            alert('文字数の上限に達しました。');
        } else {
            charCounter.style.color = '#707070';
        }
    });

    function adjustHeight() {
        const receptionContainer = document.querySelector('.reception-container');
        const introductionAreaInner = document.querySelector('.introduction-area-inner');

        if (receptionContainer && introductionAreaInner && window.innerWidth >= 890) {
            const height = introductionAreaInner.offsetHeight;
            receptionContainer.style.height = `${height}px`;
        } else if (receptionContainer) {
            receptionContainer.style.height = 'auto';
        }
    }
    
    if (document.querySelector('.reception-container') && document.querySelector('.introduction-area-inner')) {
        adjustHeight();
        window.addEventListener('resize', adjustHeight);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    var video = document.getElementById('background-video');
    if (video) {
        video.addEventListener('canplaythrough', function() {
            var videoContainer = document.querySelector('.video-container');
            if (videoContainer) {
                videoContainer.classList.add('video-loaded');
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    var element1 = document.getElementById('element1');
    if (element1) {
        element1.addEventListener('click', function() {
        });
    }

    var element2 = document.getElementById('element2');
    if (element2) {
        element2.addEventListener('click', function() {
        });
    }
});


if (typeof customUserId !== 'undefined') {
    fetch('/check_user_id/?custom_user_id=' + customUserId)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log(data);
        })
        .catch(error => {
            console.error('There was a problem with the fetch operation:', error);
        });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== LIKE FUNCTION LOADED ===');
    
    const likeButtons = document.querySelectorAll('.like-button');
    console.log('Found like buttons:', likeButtons.length);
    
    if (likeButtons.length === 0) {
        console.log('No like buttons found!');
        return;
    }
    
    likeButtons.forEach((button, index) => {
        console.log(`Button ${index}:`, button);
        console.log(`Button data-post-id:`, button.dataset.postId);
        
        button.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('=== LIKE BUTTON CLICKED ===');
            
            const postId = this.dataset.postId;
            const likeCount = this.querySelector('.like-count');
            
            console.log('Post ID:', postId);
            console.log('Current count:', likeCount.textContent);
            
            const csrfToken = document.querySelector('input[name=csrfmiddlewaretoken]').value;
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
                return response.json();
            })
            .then(data => {
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
        console.log('Date inputs not found');
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
    console.log('=== LOADING SALES REPORT ===');
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    console.log('Start date:', startDate);
    console.log('End date:', endDate);
    
    if (!startDate || !endDate) {
        console.log('Date values not found, returning');
        return;
    }
    
    const startDateFormatted = startDate.replace(/-/g, '/');
    const endDateFormatted = endDate.replace(/-/g, '/');
    
    console.log('Formatted dates:', startDateFormatted, endDateFormatted);
    
    let url;
    const pathParts = window.location.pathname.split('/').filter(part => part);
    console.log('Path parts:', pathParts);
    console.log('Full pathname:', window.location.pathname);
    
    if (pathParts.includes('group')) {
        const groupIndex = pathParts.indexOf('group');
        const groupId = pathParts[groupIndex + 1];
        url = `/mysfa/sales-report/group/${groupId}/?start_date=${startDateFormatted}&end_date=${endDateFormatted}`;
        console.log('Group URL pattern detected');
    } else {
        const userId = pathParts[pathParts.length - 1];
        let urlParams = `start_date=${startDateFormatted}&end_date=${endDateFormatted}`;
        
        
        const groupSelect = document.getElementById('group');
        if (groupSelect && groupSelect.value) {
            urlParams += `&custom_id=${encodeURIComponent(groupSelect.value)}`;
            console.log('Group selected:', groupSelect.value);
        }
        
        url = `/mysfa/sales-report/${userId}/?${urlParams}`;
        console.log('User URL pattern detected, userId:', userId);
    }
    
    console.log('Request URL:', url);
    
    fetch(url)
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data);
            console.log('Product data length:', data.product_data ? data.product_data.length : 'undefined');
            console.log('Customer data length:', data.customer_data ? data.customer_data.length : 'undefined');
            console.log('Product data details:', JSON.stringify(data.product_data, null, 2));
            console.log('Customer data details:', JSON.stringify(data.customer_data, null, 2));
            createCharts(data);
        })
        .catch(error => {
            console.error('Error loading sales report:', error);
        });
}

function createCharts(data) {
    console.log('=== CREATING CHARTS ===');
    console.log('Data received:', data);
    
    const productChartCanvas = document.getElementById('product-chart');
    const customerChartCanvas = document.getElementById('customer-chart');
    
    if (!productChartCanvas || !customerChartCanvas) {
        console.error('Chart canvases not found');
        return;
    }
    
    if (data.total_posts === 0) {
        console.log('No posts found, displaying no data message');
        displayNoDataMessage(productChartCanvas, '投稿がありません');
        displayNoDataMessage(customerChartCanvas, '投稿がありません');
        return;
    }
    
    if (data.product_data && data.product_data.length > 0) {
        displayChart(productChartCanvas, data.product_data, 'product_name', '商品別売上');
    } else {
        displayNoDataMessage(productChartCanvas, '商品データがありません');
    }
    
    if (data.customer_data && data.customer_data.length > 0) {
        displayChart(customerChartCanvas, data.customer_data, 'customer_category', '業態別売上');
    } else {
        displayNoDataMessage(customerChartCanvas, '業態データがありません');
    }
}

function displayNoDataMessage(canvas, message) {
    const parent = canvas.parentElement;
    const existingMessage = parent.querySelector('.no-data-message');
    
    if (existingMessage) {
        existingMessage.textContent = message;
    } else {
        const messageElement = document.createElement('p');
        messageElement.className = 'no-data-message';
        messageElement.textContent = message;
        canvas.style.display = 'none';
        parent.appendChild(messageElement);
    }
}

function displayChart(canvas, data, labelKey, title) {
    const parent = canvas.parentElement;
    const existingMessage = parent.querySelector('.no-data-message');
    
    if (existingMessage) {
        existingMessage.remove();
    }
    
    canvas.style.display = 'block';
    
    const ctx = canvas.getContext('2d');
    
    if (window.existingCharts && window.existingCharts[canvas.id]) {
        window.existingCharts[canvas.id].destroy();
    }
    
    if (!window.existingCharts) {
        window.existingCharts = {};
    }
    
    const colorPalette = [
        '#2C5F7A',    
        '#4A7C8C',    
        '#39AEC8',    
        '#6BC5D4',    
        '#A8D8E3',    
        '#E8F4F8'     
    ];
    
    window.existingCharts[canvas.id] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item[labelKey]),
            datasets: [{
                data: data.map(item => item.count),
                backgroundColor: colorPalette.slice(0, data.length),
                borderWidth: 2,
                borderColor: '#FFFFFF'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 15,
                    bottom: 15,
                    left: 10,
                    right: 10
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        font: {
                            size: 13
                        },
                        padding: 12,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        boxWidth: 12,
                        boxHeight: 12
                    },
                    onClick: (event, legendItem, legend) => {
                        const index = legendItem.index;
                        const label = data[index][labelKey];
                        const isProduct = labelKey === 'product_name';
                        
                        if (isProduct) {
                            window.location.href = `/mysfa/search_products/?search=${encodeURIComponent(label)}`;
                        } else {
                            window.location.href = `/mysfa/search_customers/?search=${encodeURIComponent(label)}`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1200,
                easing: 'easeOutQuart'
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const label = data[index][labelKey];
                    const isProduct = labelKey === 'product_name';
                    
                    if (isProduct) {
                        window.location.href = `/mysfa/search_products/?search=${encodeURIComponent(label)}`;
                    } else {
                        window.location.href = `/mysfa/search_customers/?search=${encodeURIComponent(label)}`;
                    }
                }
            }
        }
    });
    
    const chart = window.existingCharts[canvas.id];
    
    setTimeout(() => {
        if (chart && chart.canvas) {
            adjustChartHeights();
        }
    }, 200);
}

function adjustChartHeights() {
    const productChart = document.getElementById('product-chart');
    const customerChart = document.getElementById('customer-chart');
    
    if (!productChart || !customerChart) return;
    
    const productWrapper = productChart.closest('.chart-wrapper');
    const customerWrapper = customerChart.closest('.chart-wrapper');
    
    if (!productWrapper || !customerWrapper) return;
    
    setTimeout(() => {
        const productChartInstance = window.existingCharts['product-chart'];
        const customerChartInstance = window.existingCharts['customer-chart'];
        
        if (!productChartInstance || !customerChartInstance) return;
        
        const productCanvas = productChartInstance.canvas;
        const customerCanvas = customerChartInstance.canvas;
        
        const productWidth = productCanvas.width;
        const productHeight = productCanvas.height;
        const customerWidth = customerCanvas.width;
        const customerHeight = customerCanvas.height;
        
        console.log('Product chart size:', productWidth, 'x', productHeight);
        console.log('Customer chart size:', customerWidth, 'x', customerHeight);
        
        if (productWidth > customerWidth || productHeight > customerHeight) {
            const scaleX = productWidth / customerWidth;
            const scaleY = productHeight / customerHeight;
            const scale = Math.max(scaleX, scaleY);
            
            console.log('Scaling customer chart by:', scale);
            
            customerCanvas.style.width = `${productWidth}px`;
            customerCanvas.style.height = `${productHeight}px`;
            customerWrapper.style.minHeight = `${productWrapper.offsetHeight}px`;
        } else if (customerWidth > productWidth || customerHeight > productHeight) {
            const scaleX = customerWidth / productWidth;
            const scaleY = customerHeight / productHeight;
            const scale = Math.max(scaleX, scaleY);
            
            console.log('Scaling product chart by:', scale);
            
            productCanvas.style.width = `${customerWidth}px`;
            productCanvas.style.height = `${customerHeight}px`;
            productWrapper.style.minHeight = `${customerWrapper.offsetHeight}px`;
        }
        
        const maxHeight = Math.max(productWrapper.offsetHeight, customerWrapper.offsetHeight);
        const chartsContainer = document.querySelector('.charts-container');
        if (chartsContainer) {
            chartsContainer.style.minHeight = `${maxHeight}px`;
        }
    }, 500);
}

document.addEventListener('DOMContentLoaded', function() {
    initializeSalesReport();
});