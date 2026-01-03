document.addEventListener("DOMContentLoaded", function () {
    const counter = document.getElementById("char-counter");
    if (!counter) return;
  
    const textarea = document.getElementById("id_contents");
    if (!textarea) return;
  
    const max = 100;
    const update = () => {
      const len = (textarea.value || "").length;
      counter.textContent = `${len}/${max}`;
    };
  
    textarea.addEventListener("input", update);
    update();
  });