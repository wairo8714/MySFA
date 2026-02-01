document.addEventListener("DOMContentLoaded", () => {
  const containers = document.querySelectorAll(".post-comments");
  if (!containers.length) return;

  function setCollapsed(container, collapsed) {
    const body = container.querySelector(".post-comments__body");
    const btn = container.querySelector(".post-comments__toggle");
    if (!body || !btn) return;

    if (collapsed) {
      body.style.maxHeight = "0px";
      container.classList.add("is-collapsed");
      btn.setAttribute("aria-expanded", "false");
    } else {
      body.style.maxHeight = body.scrollHeight + "px";
      container.classList.remove("is-collapsed");
      btn.setAttribute("aria-expanded", "true");
    }
  }

  for (const container of containers) {
    const body = container.querySelector(".post-comments__body");
    const btn = container.querySelector(".post-comments__toggle");
    if (!body || !btn) continue;

    setCollapsed(container, true);

    btn.addEventListener("click", () => {
      const collapsed = container.classList.contains("is-collapsed");
      setCollapsed(container, !collapsed);
    });

    const textarea = container.querySelector(".post-comment-form__textarea");
    if (textarea) {
      textarea.addEventListener("input", () => {
        if (!container.classList.contains("is-collapsed")) {
          body.style.maxHeight = body.scrollHeight + "px";
        }
      });
    }
  }

  window.addEventListener("load", () => {
    for (const container of containers) {
      if (!container.classList.contains("is-collapsed")) {
        const body = container.querySelector(".post-comments__body");
        if (body) body.style.maxHeight = body.scrollHeight + "px";
      }
    }
  });
});

