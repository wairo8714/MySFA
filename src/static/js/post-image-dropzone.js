document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("id_image");
  const zone = document.getElementById("post-image-dropzone");
  const preview = document.getElementById("post-image-preview");
  const hint = document.getElementById("post-image-hint");
  const nameEl = document.getElementById("post-image-name");
  const clearBtn = document.getElementById("post-image-clear");

  if (!input || !zone) return;

  function reset() {
    input.value = "";
    if (nameEl) nameEl.textContent = "";
    if (preview) {
      preview.removeAttribute("src");
      preview.style.display = "none";
    }
    if (hint) hint.style.display = "";
    if (clearBtn) clearBtn.style.display = "none";
  }

  function setPreview(file) {
    if (!file) return;
    if (nameEl) nameEl.textContent = file.name || "";

    if (preview && file.type && file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      preview.src = url;
      preview.style.display = "block";
      if (hint) hint.style.display = "none";
      if (clearBtn) clearBtn.style.display = "inline-flex";
      preview.onload = () => URL.revokeObjectURL(url);
    }
  }

  zone.addEventListener("click", (e) => {
    e.preventDefault();
    input.click();
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      reset();
    });
  }

  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (file) setPreview(file);
    else reset();
  });

  function prevent(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ["dragenter", "dragover"].forEach((t) => {
    zone.addEventListener(t, (e) => {
      prevent(e);
      zone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((t) => {
    zone.addEventListener(t, (e) => {
      prevent(e);
      zone.classList.remove("is-dragover");
    });
  });

  zone.addEventListener("drop", (e) => {
    const files = e.dataTransfer && e.dataTransfer.files;
    if (!files || !files.length) return;

    const file = files[0];
    if (file && file.type && !file.type.startsWith("image/")) return;

    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    setPreview(file);
  });
});

