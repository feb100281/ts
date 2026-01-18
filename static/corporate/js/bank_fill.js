// corporate/static/corporate/js/bank_fill.js

document.addEventListener("DOMContentLoaded", function () {
    const bikInput = document.querySelector("#id_bik");
    if (!bikInput) return;   // Если на странице нет поля БИК — ничего не делаем

    let btn = document.getElementById("fill-by-bik");
    if (!btn) {
        const parent = bikInput.parentElement;

        const wrapper = document.createElement("div");
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";
        wrapper.style.gap = "8px";

        parent.insertBefore(wrapper, bikInput);
        wrapper.appendChild(bikInput);

        btn = document.createElement("button");
        btn.type = "button";
        btn.id = "fill-by-bik";
        btn.textContent = "📥 Заполнить по БИК";
        btn.className = "btn btn-success";
        btn.style.whiteSpace = "nowrap";

        wrapper.appendChild(btn);
    }

    btn.addEventListener("click", function () {
        let hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "_fill_by_bik";
        hidden.value = "1";
        bikInput.form.appendChild(hidden);

        bikInput.form.submit();
    });
});


