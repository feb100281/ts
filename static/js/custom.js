document.addEventListener("click", function (event) {
    // ищем клик по шапке карточки оценки или по кнопке-стрелочке
    const header = event.target.closest(".valuation-inline__header");
    if (!header) {
        return;
    }

    const box = header.closest(".valuation-inline");
    if (!box) {
        return;
    }

    // переключаем состояние
    if (box.classList.contains("is-collapsed")) {
        box.classList.remove("is-collapsed");
        box.classList.add("is-open");
    } else {
        box.classList.add("is-collapsed");
        box.classList.remove("is-open");
    }
});
