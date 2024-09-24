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

        if (window.innerWidth >= 890) {
            const height = introductionAreaInner.offsetHeight;
            receptionContainer.style.height = `${height}px`;
        } else {
            receptionContainer.style.height = 'auto';
        }
    }
    adjustHeight();
    window.addEventListener('resize', adjustHeight);
});

// ビデオフェードイン
document.addEventListener('DOMContentLoaded', function() {
    var video = document.getElementById('background-video');
    video.addEventListener('canplaythrough', function() {
        var videoContainer = document.querySelector('.video-container');
        videoContainer.classList.add('video-loaded');
    });
});

document.addEventListener('DOMContentLoaded', function() {
    var element1 = document.getElementById('element1');
    if (element1) {
        element1.addEventListener('click', function() {
            // クリック時の処理
        });
    }

    var element2 = document.getElementById('element2');
    if (element2) {
        element2.addEventListener('click', function() {
            // クリック時の処理
        });
    }
});

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