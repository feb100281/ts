document.addEventListener("DOMContentLoaded", function () {
    const rows = document.querySelectorAll("#result_list tbody tr");

    let prevKey = null;
    let groupIndex = 0;

    rows.forEach((row) => {
        const cells = row.querySelectorAll("td");
        if (!cells.length) return;

        // Важно: индексы зависят от list_display
        // 0 = checkbox
        // 1 = id_col
        // 2 = date_col
        // 3 = group_marker
        // 4 = owner_col
        // 5 = contract_col
        // ...
        const dateCell = cells[1];
        const groupCell = cells[2];
        const contractCell = cells[4];

        if (!dateCell || !groupCell || !contractCell) return;

        const dateText = dateCell.innerText.trim();
        const contractText = contractCell.innerText.trim().split("\n")[0].trim();
        const groupText = groupCell.innerText.trim();

        const isGrouped = groupText !== "—";

        if (!isGrouped) {
            row.classList.add("manual-row-single");
            prevKey = null;
            return;
        }

        const key = `${dateText}__${contractText}`;

        if (key !== prevKey) {
            groupIndex += 1;
            prevKey = key;
        }

        row.dataset.groupKey = key;
        row.dataset.groupIndex = groupIndex;

        if (groupIndex % 2 === 0) {
            row.classList.add("manual-row-group-even");
        } else {
            row.classList.add("manual-row-group-odd");
        }
    });
});