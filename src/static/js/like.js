function getCookie(name) {
  const value = `; ${document.cookie || ""}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

document.addEventListener("DOMContentLoaded", function () {
  const likeButtons = document.querySelectorAll(".like-button");
  if (!likeButtons.length) return;

  const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
  const csrfToken = (csrfInput && csrfInput.value) || getCookie("csrftoken");
  if (!csrfToken) return;

  likeButtons.forEach((button) => {
    button.addEventListener("click", async function (e) {
      e.preventDefault();

      const postId = this.dataset.postId;
      if (!postId) return;

      const likeCount = this.querySelector(".like-count");
      const url = `/mysfa/like-post/${postId}/`;

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
            Accept: "application/json",
          },
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) return;

        if (data.status === "liked" || data.status === "unliked") {
          if (likeCount) likeCount.textContent = String(data.count);
          if (data.status === "liked") {
            button.classList.add("liked");
          } else {
            button.classList.remove("liked");
          }
        }
      } catch (_err) {}
    });
  });
});
