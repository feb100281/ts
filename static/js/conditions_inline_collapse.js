document.addEventListener("click", function (event) {
  const header = event.target.closest(".valuation-inline__header");
  if (!header) return;

  const box = header.closest(".valuation-inline");
  if (!box) return;

  // не мешаем клику по checkbox "Удалить"
  if (event.target.closest("input[type='checkbox'], label")) return;

  if (box.classList.contains("is-collapsed")) {
    box.classList.remove("is-collapsed");
    box.classList.add("is-open");
  } else {
    box.classList.add("is-collapsed");
    box.classList.remove("is-open");
  }
});