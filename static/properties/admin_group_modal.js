document.addEventListener("DOMContentLoaded", function () {
  const body = document.body;

  const backdrop = document.createElement("div");
  backdrop.className = "group-avg-modal-backdrop";
  backdrop.innerHTML = `
    <div class="group-avg-modal">
      <div class="group-avg-modal-header">
        <span class="group-avg-modal-title">Детализация</span>
        <button type="button" class="group-avg-modal-close" aria-label="Закрыть">×</button>
      </div>
      <div class="group-avg-modal-body"></div>
    </div>
  `;
  body.appendChild(backdrop);

  const modalBody = backdrop.querySelector(".group-avg-modal-body");
  const modalTitle = backdrop.querySelector(".group-avg-modal-title");
  const closeBtn = backdrop.querySelector(".group-avg-modal-close");

  function openModal(html, title) {
    modalBody.innerHTML = html;
    if (title) modalTitle.textContent = title;
    backdrop.classList.add("is-visible");
  }

  function closeModal() {
    backdrop.classList.remove("is-visible");
  }

  closeBtn.addEventListener("click", closeModal);
  backdrop.addEventListener("click", function (e) {
    if (e.target === backdrop) closeModal();
  });
  body.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeModal();
  });

  // общий обработчик для всех 👁
  body.addEventListener("click", function (e) {
    const trigger = e.target.closest(".group-details-trigger");
    if (!trigger) return;

    e.preventDefault();

    const container = trigger.closest("div");
    if (!container) return;

    const hidden = container.querySelector(".group-details-content");
    if (!hidden) return;

    const type = trigger.getAttribute("data-details-type");
    let title = "Детализация";

    if (type === "objects") {
      title = "Состав группы: объекты";
    } else if (type === "avg") {
      title = "Детализация средней стоимости";
    }

    openModal(hidden.innerHTML, title);
  });
});
