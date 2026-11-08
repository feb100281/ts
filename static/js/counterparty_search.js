document.addEventListener('DOMContentLoaded', function () {
  if (!window.location.pathname.includes('/admin/')) return;

  function enhanceSearchField() {
    const form = document.querySelector('#changelist-search');
    if (!form) return;

    const input = form.querySelector('input[name="q"]');
    if (!input || input.dataset.enhanced) return;

    input.dataset.enhanced = "true";
    input.setAttribute('placeholder', '');
    input.setAttribute('type', 'search');

    // обёртка для позиционирования крестика
    const wrap = document.createElement('span');
    wrap.className = 'admin-search-wrap';
    input.parentElement.insertBefore(wrap, input);
    wrap.appendChild(input);

    const searchIcon = document.createElement('span');
    searchIcon.className = 'admin-search-icon';
    
    wrap.appendChild(searchIcon);

    // крестик
    const clearBtn = document.createElement('span');
    clearBtn.className = 'admin-clear-btn';
    clearBtn.textContent = '×';
    clearBtn.title = 'Очистить';
    clearBtn.addEventListener('click', () => {
      input.value = '';
      input.focus();
      const url = new URL(window.location.href);
      url.searchParams.delete('q');
      url.searchParams.delete('p');
      const qs = url.searchParams.toString();
      window.location.href = url.pathname + (qs ? `?${qs}` : '');
    });
    wrap.appendChild(clearBtn);

    // если пользователь стёр вручную — тоже сбросим выборку
    input.addEventListener('input', () => {
      if (input.value === '' && new URL(window.location.href).searchParams.has('q')) {
        const url = new URL(window.location.href);
        url.searchParams.delete('q');
        url.searchParams.delete('p');
        const qs = url.searchParams.toString();
        window.location.href = url.pathname + (qs ? `?${qs}` : '');
      }
    });
  }

  setTimeout(enhanceSearchField, 100);
  setTimeout(enhanceSearchField, 400);
  setTimeout(enhanceSearchField, 1000);
});




