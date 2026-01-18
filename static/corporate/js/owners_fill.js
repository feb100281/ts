// corporate/static/corporate/js/owners_fill.js

document.addEventListener("DOMContentLoaded", function () {
    const innInput = document.querySelector("#id_inn");
    if (!innInput) return;

    let btn = document.getElementById("fill-by-inn");
    if (!btn) {
        const parent = innInput.parentElement;
        const wrapper = document.createElement("div");
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";
        wrapper.style.gap = "8px";

        parent.insertBefore(wrapper, innInput);
        wrapper.appendChild(innInput);

        btn = document.createElement("button");
        btn.type = "button";
        btn.id = "fill-by-inn";
        btn.textContent = "📥 Заполнить по ИНН";
        btn.className = "btn btn-success";
        btn.style.whiteSpace = "nowrap";

        wrapper.appendChild(btn);
    }

    btn.addEventListener("click", function () {
        let hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "_fill_by_inn";
        hidden.value = "1";
        innInput.form.appendChild(hidden);
        innInput.form.submit();
    });
});
