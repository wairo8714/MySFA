(function () {
  function qsa(sel) {
    return Array.prototype.slice.call(document.querySelectorAll(sel));
  }

  function getCheckboxes() {
    return qsa(".master-select-checkbox");
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

  function init() {
    var selectAllBtn = document.getElementById("select-all-btn");
    var bulkForm = document.getElementById("bulk-delete-form");
    var bulkDeleteBtn = document.getElementById("bulk-delete-btn");
    var bulkEditBtn = document.getElementById("bulk-edit-btn");
    var selectedCountEl = document.getElementById("selected-count");

    if (!selectAllBtn && !bulkForm) return;

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
          window.alert("変更する業態を1件だけ選択してください。");
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
          window.alert("削除する業態を選択してください。");
          return;
        }
        var ok = window.confirm("選択した業態（" + selected.length + "件）を削除します。よろしいですか？");
        if (!ok) e.preventDefault();
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

