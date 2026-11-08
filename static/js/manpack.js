// Раскрытие статей P&L: статья → подстатья → контрагент
document.addEventListener("click", function (e) {
  var tr = e.target.closest && e.target.closest(".mp-table.drill tr.exp");
  if (!tr) return;
  var key = tr.getAttribute("data-key");
  var open = tr.classList.toggle("open");
  tr.parentElement.querySelectorAll("tr[data-parent]").forEach(function (r) {
    var p = r.getAttribute("data-parent");
    if (p === key) {
      r.classList.toggle("show", open);
      if (!open) r.classList.remove("open");
    } else if (!open && p.indexOf(key + "/") === 0) {
      r.classList.remove("show", "open");
    }
  });
});
