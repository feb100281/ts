document.addEventListener("DOMContentLoaded", function () {
    const rows = Array.from(document.querySelectorAll("#result_list tbody tr"));
    if (!rows.length) return;

    const groups = new Map();

    // Клик по строке
    rows.forEach((row) => {
        const link = row.querySelector("th a");
        if (link) {
            row.style.cursor = "pointer";

            row.addEventListener("click", function (e) {
                if (e.target.closest("a")) return;
                if (e.target.closest("input")) return;
                if (e.target.closest("select")) return;
                if (e.target.closest("button")) return;
                if (e.target.closest("label")) return;
                if (e.target.closest("form")) return;

                window.location.href = link.href;
            });
        }
    });

    // Собираем строки по server-side ключу группы
    rows.forEach((row) => {
        const contractCell = row.querySelector(".manual-contract-cell");
        if (!contractCell) {
            row.classList.add("manual-row-single");
            return;
        }

        const groupKey = contractCell.dataset.groupKey || "";
        const groupCount = parseInt(contractCell.dataset.groupCount || "1", 10);

        if (!groupKey || groupCount <= 1) {
            row.classList.add("manual-row-single");
            return;
        }

        if (!groups.has(groupKey)) {
            groups.set(groupKey, []);
        }

        groups.get(groupKey).push(row);
    });

    // Красим группы
    let groupIndex = 0;

    groups.forEach((groupRows, groupKey) => {
        if (groupRows.length <= 1) {
            groupRows.forEach((row) => row.classList.add("manual-row-single"));
            return;
        }

        groupIndex += 1;
        const parityClass = groupIndex % 2 === 0
            ? "manual-row-group-even"
            : "manual-row-group-odd";

        groupRows.forEach((row, idx) => {
            row.dataset.groupKey = groupKey;
            row.dataset.groupIndex = String(groupIndex);
            row.classList.add(parityClass);

            if (idx === 0) {
                row.classList.add("group-start");
            }
            if (idx === groupRows.length - 1) {
                row.classList.add("group-end");
            }
        });
    });
});