document.addEventListener("DOMContentLoaded", function () {
  const userIdInput = document.getElementById("registeringUserID");
  const messageEl = document.getElementById("user-id-message");
  if (!userIdInput || !messageEl) return;

  let timer = null;
  let lastValue = "";

  function setMessage(text, ok) {
    messageEl.textContent = text || "";
    if (ok === true) {
      messageEl.style.color = "#2e7d32";
    } else if (ok === false) {
      messageEl.style.color = "#c62828";
    } else {
      messageEl.style.color = "";
    }
  }

  async function check() {
    const userId = (userIdInput.value || "").trim();
    if (!userId) {
      setMessage("", null);
      return;
    }
    if (userId === lastValue) return;
    lastValue = userId;

    try {
      const res = await fetch(
        `/accounts/check_user_id/?custom_user_id=${encodeURIComponent(userId)}`,
        { headers: { Accept: "application/json" } }
      );
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setMessage("このユーザーIDは使用可能です。", true);
      } else {
        setMessage(data.error || "このユーザーIDは使用できません。", false);
      }
    } catch (_e) {
      setMessage("通信エラーが発生しました。", false);
    }
  }

  userIdInput.addEventListener("input", function () {
    if (timer) clearTimeout(timer);
    timer = setTimeout(check, 250);
  });
  userIdInput.addEventListener("blur", check);
});
