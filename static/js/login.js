document.addEventListener("DOMContentLoaded", function () {
    const pass = document.getElementById('password');
    const btn  = document.getElementById('togglePass');
    const hint = document.getElementById('capsHint');

    if (btn && pass) {
        btn.addEventListener('click', function () {
            const show = pass.type === 'password';
            pass.type = show ? 'text' : 'password';
            this.setAttribute('aria-label', show ? 'Скрыть пароль' : 'Показать пароль');
            this.title = show ? 'Скрыть пароль' : 'Показать пароль';
        });

        // CapsLock предупреждение
        ['keydown', 'keyup'].forEach(evt => {
            pass.addEventListener(evt, function (e) {
                if (!('getModifierState' in e)) return;
                hint.style.display = e.getModifierState('CapsLock') ? 'inline' : 'none';
            });
        });
    }
});
