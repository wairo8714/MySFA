(function () {
  function getCookie(name) {
    var value = null;
    if (document.cookie && document.cookie !== "") {
      var cookies = document.cookie.split(";");
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + "=")) {
          value = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return value;
  }

  function qsa(sel) {
    return Array.prototype.slice.call(document.querySelectorAll(sel));
  }

  function getCheckboxes() {
    return qsa(".master-select-checkbox");
  }

  function updateBulkDeleteState(cbs, deleteBtn) {
    if (!deleteBtn) return;
    var selected = cbs.filter(function (cb) { return cb.checked; });
    deleteBtn.disabled = selected.length === 0;
    deleteBtn.setAttribute("aria-disabled", deleteBtn.disabled ? "true" : "false");
  }

  function updateBulkEditState(cbs, editBtn) {
    if (!editBtn) return;
    var selected = cbs.filter(function (cb) { return cb.checked; });
    editBtn.disabled = selected.length !== 1;
    editBtn.setAttribute("aria-disabled", editBtn.disabled ? "true" : "false");
  }

  function updateSelectedCount(cbs, countEl) {
    if (!countEl) return;
    var selected = cbs.filter(function (cb) { return cb.checked; });
    countEl.textContent = "選択中：" + selected.length + "件";
  }

  function updateSelectAllLabel(selectAllBtn, cbs) {
    if (!selectAllBtn) return;
    if (cbs.length === 0) return;
    var allChecked = cbs.every(function (cb) { return cb.checked; });
    selectAllBtn.textContent = allChecked ? "全解除" : "全選択";
  }

  function init() {
    var selectAllBtn = document.getElementById("select-all-btn");
    var bulkForm = document.getElementById("bulk-delete-form");
    var bulkDeleteBtn = document.getElementById("bulk-delete-btn");
    var bulkEditBtn = document.getElementById("bulk-edit-btn");
    var selectedCountEl = document.getElementById("selected-count");
    var csvModal = document.getElementById("csv-modal");
    var csvOverlay = document.getElementById("csv-modal-overlay");
    var csvOpenBtn = document.getElementById("open-csv-modal-btn");
    var csvCloseBtn = document.getElementById("csv-modal-close-btn");
    var csvFileInput = document.getElementById("csv-file-input");
    var csvValidateBtn = document.getElementById("csv-validate-btn");
    var csvSubmitBtn = document.getElementById("csv-submit-btn");
    var csvResult = document.getElementById("csv-result");
    var csvValidateUrl = csvValidateBtn ? csvValidateBtn.getAttribute("data-validate-url") : null;
    var csvSubmitUrl = csvSubmitBtn ? csvSubmitBtn.getAttribute("data-submit-url") : null;
    var lastValidatedOk = false;

    function refreshBulkUi() {
      var cbs = getCheckboxes();
      updateBulkDeleteState(cbs, bulkDeleteBtn);
      updateBulkEditState(cbs, bulkEditBtn);
      updateSelectedCount(cbs, selectedCountEl);
      updateSelectAllLabel(selectAllBtn, cbs);
    }

    refreshBulkUi();

    document.addEventListener("change", function (e) {
      var t = e.target;
      if (!t || !t.classList || !t.classList.contains("master-select-checkbox")) return;
      refreshBulkUi();
    });

    if (selectAllBtn) {
      selectAllBtn.addEventListener("click", function () {
        var cbs = getCheckboxes();
        if (cbs.length === 0) return;
        var allChecked = cbs.every(function (cb) { return cb.checked; });
        cbs.forEach(function (cb) { cb.checked = !allChecked; });
        refreshBulkUi();
      });
    }

    if (bulkEditBtn) {
      bulkEditBtn.addEventListener("click", function () {
        var cbs = getCheckboxes();
        var selected = cbs.filter(function (cb) { return cb.checked; });
        if (selected.length !== 1) {
          window.alert("変更する商品を1件だけ選択してください。");
          return;
        }
        var id = selected[0].value;
        var tpl = bulkEditBtn.getAttribute("data-edit-url-template") || "";
        if (!tpl || tpl.indexOf("__ID__") < 0) return;
        window.location.href = tpl.replace("__ID__", encodeURIComponent(String(id)));
      });
    }

    if (bulkForm) {
      bulkForm.addEventListener("submit", function (e) {
        var cbs = getCheckboxes();
        var selected = cbs.filter(function (cb) { return cb.checked; });
        if (selected.length === 0) {
          e.preventDefault();
          window.alert("削除する商品を選択してください。");
          return;
        }
        var ok = window.confirm("選択した商品（" + selected.length + "件）の削除依頼を送信します。よろしいですか？");
        if (!ok) e.preventDefault();
      });
    }

    function openCsvModal() {
      if (!csvModal || !csvOverlay) return;
      csvOverlay.classList.add("is-open");
      csvModal.classList.add("is-open");
      csvOverlay.setAttribute("aria-hidden", "false");
      csvModal.setAttribute("aria-hidden", "false");

      lastValidatedOk = false;
      if (csvFileInput) csvFileInput.value = "";
      if (csvValidateBtn) csvValidateBtn.disabled = true;
      setCsvSubmitEnabled(false);
      setCsvResult("", "");
    }

    function closeCsvModal() {
      if (!csvModal || !csvOverlay) return;
      csvOverlay.classList.remove("is-open");
      csvModal.classList.remove("is-open");
      csvOverlay.setAttribute("aria-hidden", "true");
      csvModal.setAttribute("aria-hidden", "true");
    }

    if (csvOpenBtn) {
      csvOpenBtn.addEventListener("click", function () {
        openCsvModal();
      });
    }

    if (csvCloseBtn) {
      csvCloseBtn.addEventListener("click", function () {
        closeCsvModal();
      });
    }

    if (csvOverlay) {
      csvOverlay.addEventListener("click", function () {
        closeCsvModal();
      });
    }

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeCsvModal();
    });

    function setCsvResult(kind, html) {
      if (!csvResult) return;
      csvResult.classList.remove("is-ok", "is-error");
      if (kind) csvResult.classList.add(kind === "ok" ? "is-ok" : "is-error");
      csvResult.innerHTML = html;
    }

    function setCsvSubmitEnabled(enabled) {
      if (!csvSubmitBtn) return;
      csvSubmitBtn.disabled = !enabled;
      csvSubmitBtn.setAttribute("aria-disabled", enabled ? "false" : "true");
    }

    function buildCsvEndpoint(type) {
      if (!bulkForm) return null;
      var action = bulkForm.getAttribute("action") || "";
      return action.replace(/\/product-master\/delete-request\/?$/, "/product-master/" + type + "/");
    }

    if (!csvValidateUrl) csvValidateUrl = buildCsvEndpoint("csv-validate");
    if (!csvSubmitUrl) csvSubmitUrl = buildCsvEndpoint("csv-submit");

    if (csvFileInput) {
      csvFileInput.addEventListener("change", function () {
        lastValidatedOk = false;
        if (csvValidateBtn) {
          csvValidateBtn.disabled = !(csvFileInput.files && csvFileInput.files.length > 0);
        }
        setCsvSubmitEnabled(false);
        setCsvResult("", "");
      });
    }

    if (csvValidateBtn) {
      csvValidateBtn.addEventListener("click", function () {
        if (!csvFileInput || !csvFileInput.files || csvFileInput.files.length === 0) {
          setCsvResult("error", "CSVファイルを選択してください。");
          setCsvSubmitEnabled(false);
          return;
        }
        if (!csvValidateUrl) {
          setCsvResult("error", "検証URLが見つかりませんでした。");
          setCsvSubmitEnabled(false);
          return;
        }

        var fd = new FormData();
        fd.append("file", csvFileInput.files[0]);

        csvValidateBtn.disabled = true;
        setCsvSubmitEnabled(false);
        setCsvResult("", "チェック中…");

        fetch(csvValidateUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": getCookie("csrftoken") },
          body: fd
        })
          .then(function (res) {
            return res.text().then(function (t) {
              var j = null;
              try { j = JSON.parse(t); } catch (_) {}
              return { status: res.status, ok: res.ok, json: j, text: t };
            });
          })
          .then(function (r) {
            if (!r.ok) {
              setCsvResult("error", "チェックに失敗しました（" + r.status + "）。もう一度お試しください。");
              setCsvSubmitEnabled(false);
              return;
            }

            var j = r.json || {};
            var total = j.total_count || 0;
            var err = j.error_count || 0;
            var okc = j.ok_count || 0;

            var html = "アップロード数: <b>" + total + "</b> / エラー数: <b>" + err + "</b> / 登録依頼数: <b>" + okc + "</b>";
            if (j.errors && j.errors.length) {
              html += "<ul>" + j.errors.map(function (e) {
                var prefix = (e.row && e.row > 0) ? ("行" + e.row + ": ") : "";
                return "<li>" + prefix + (e.message || "") + "</li>";
              }).join("") + "</ul>";
            }

            lastValidatedOk = !!j.ok;
            if (lastValidatedOk) {
              setCsvResult("ok", html);
              setCsvSubmitEnabled(true);
            } else {
              setCsvResult("error", html);
              setCsvSubmitEnabled(false);
            }
          })
          .catch(function () {
            setCsvResult("error", "チェックに失敗しました。しばらくしてから再度お試しください。");
            setCsvSubmitEnabled(false);
          })
          .finally(function () {
            csvValidateBtn.disabled = false;
          });
      });
    }

    if (csvSubmitBtn) {
      csvSubmitBtn.addEventListener("click", function () {
        if (!lastValidatedOk) return;
        if (!csvSubmitUrl) {
          setCsvResult("error", "登録依頼URLが見つかりませんでした。");
          setCsvSubmitEnabled(false);
          return;
        }
        if (!csvFileInput || !csvFileInput.files || csvFileInput.files.length === 0) {
          setCsvResult("error", "CSVファイルを選択してください。");
          setCsvSubmitEnabled(false);
          return;
        }

        var ok = window.confirm("CSVの内容で登録依頼を送信します。よろしいですか？");
        if (!ok) return;

        var fd = new FormData();
        fd.append("file", csvFileInput.files[0]);

        csvSubmitBtn.disabled = true;
        csvSubmitBtn.textContent = "送信中…";

        fetch(csvSubmitUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": getCookie("csrftoken") },
          body: fd
        })
          .then(function (res) {
            window.location.href = window.location.href;
          })
          .catch(function () {
            csvSubmitBtn.disabled = false;
            csvSubmitBtn.textContent = "登録依頼";
            setCsvResult("error", "登録依頼に失敗しました。しばらくしてから再度お試しください。");
          });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();


