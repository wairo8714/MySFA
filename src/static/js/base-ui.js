document.addEventListener("DOMContentLoaded", function () {
  const menuOpen = document.querySelector("#humburger-icon");
  const menuClose = document.querySelector(".overlay");
  const sidebar = document.querySelector(".sidebar-inner");
  const overlay = document.querySelector(".overlay");

  const menuOptions = {
    duration: 700,
    easing: "ease",
    fill: "forwards",
  };

  if (sidebar && overlay) {
    sidebar.style.transition = `transform ${menuOptions.duration}ms ${menuOptions.easing} ${menuOptions.fill}`;
    overlay.style.transition = `background-color ${menuOptions.duration}ms ${menuOptions.easing}`;
  }

  if (menuOpen) {
    menuOpen.addEventListener("click", () => {
      if (sidebar) sidebar.style.transform = "translateX(0)";
      if (overlay) {
        overlay.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
        overlay.style.display = "block";
      }
    });
  }

  if (menuClose) {
    menuClose.addEventListener("click", () => {
      if (sidebar) sidebar.style.transform = "translateX(100%)";
      if (overlay) {
        overlay.style.backgroundColor = "rgba(0, 0, 0, 0)";
        setTimeout(() => {
          overlay.style.display = "none";
        }, menuOptions.duration);
      }
    });
  }

  const dropdownToggles = document.querySelectorAll(".dropdown-toggle");
  dropdownToggles.forEach((toggle) => {
    toggle.addEventListener("click", function (e) {
      if (e && typeof e.preventDefault === "function") e.preventDefault();
      const dropdownMenu = this.nextElementSibling;
      const dropdownArrow = this.querySelector(".dropdown-arrow");
      if (dropdownMenu) dropdownMenu.classList.toggle("show");
      if (dropdownArrow) dropdownArrow.classList.toggle("rotate");
      const expanded = dropdownMenu && dropdownMenu.classList.contains("show");
      this.setAttribute("aria-expanded", expanded ? "true" : "false");
    });
  });

  document.addEventListener("click", function (event) {
    dropdownToggles.forEach((toggle) => {
      const dropdownMenu = toggle.nextElementSibling;
      const dropdownArrow = toggle.querySelector(".dropdown-arrow");
      if (
        dropdownMenu &&
        dropdownMenu.classList.contains("show") &&
        !toggle.contains(event.target) &&
        !dropdownMenu.contains(event.target)
      ) {
        dropdownMenu.classList.remove("show");
        if (dropdownArrow) dropdownArrow.classList.remove("rotate");
      }
    });
  });

  const postModal = document.getElementById("postModal");
  const openModalBtn = document.getElementById("openModalBtn");
  const closeModalBtn = document.getElementById("closeModalBtn");

  if (openModalBtn) {
    openModalBtn.addEventListener("click", function () {
      if (postModal) postModal.style.display = "block";
    });
  }
  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", function () {
      if (postModal) postModal.style.display = "none";
    });
  }
  window.addEventListener("click", function (event) {
    if (postModal && event.target === postModal) {
      postModal.style.display = "none";
    }
  });

  const messageElement = document.querySelector(".message");
  if (messageElement) {
    setTimeout(() => {
      messageElement.style.opacity = "0";
    }, 3000);
  }

  const scrollToTopBtn = document.getElementById("scrollToTopBtn");
  if (scrollToTopBtn) {
    window.addEventListener("scroll", function () {
      if (
        document.body.scrollTop > 20 ||
        document.documentElement.scrollTop > 20
      ) {
        scrollToTopBtn.style.display = "block";
      } else {
        scrollToTopBtn.style.display = "none";
      }
    });

    scrollToTopBtn.addEventListener("click", function () {
      document.body.scrollTop = 0;
      document.documentElement.scrollTop = 0;
    });
  }
});

function toggleAccordion(accordionId) {
  const accordion = document.getElementById(accordionId);
  const icon = document.getElementById(accordionId.replace("accordion", "icon"));
  if (!accordion || !icon) return;

  if (accordion.style.display === "none" || accordion.style.display === "") {
    accordion.style.display = "block";
    icon.textContent = "-";
  } else {
    accordion.style.display = "none";
    icon.textContent = "+";
  }
}

function showCustomers(productId) {
  const customers = document.getElementById(`customers-${productId}`);
  if (!customers) return;
  customers.classList.toggle("show");
}

function showCustomerDetails(customerId) {
  const details = document.getElementById(`details-${customerId}`);
  if (!details) return;
  details.classList.toggle("show");
}


