document.addEventListener('DOMContentLoaded', function () {
  const innInput   = document.getElementById('id_tax_id');
  if (!innInput) return;

  const ceoInput   = document.getElementById('id_ceo');
  const hiddenFlag = document.getElementById('id_ceo_hidden_by_fns');
  const adminForm  = document.querySelector('form');

  // ===== История изменений (persist) =========================================
  let wasInput = document.getElementById('id_was_notes');
  if (!wasInput) {
    wasInput = document.createElement('input');
    wasInput.type = 'hidden';
    wasInput.id = 'id_was_notes';
    wasInput.name = 'was_notes';
    if (adminForm) adminForm.appendChild(wasInput);
  }
  let WAS = {};
  try { WAS = wasInput.value ? JSON.parse(wasInput.value) : {}; } catch (_) { WAS = {}; }
  function syncWas(){ wasInput.value = JSON.stringify(WAS||{}); }
  function setWas(key, prev){ if (prev) { WAS[key]=prev; syncWas(); } }

  // 🔹 Флаг "данные подтянуты по ИНН" — улетит в POST как checko_from_inn=1
  let checkoFlag = document.getElementById('id_checko_from_inn');
  if (!checkoFlag) {
    checkoFlag = document.createElement('input');
    checkoFlag.type  = 'hidden';
    checkoFlag.id    = 'id_checko_from_inn';
    checkoFlag.name  = 'checko_from_inn';
    checkoFlag.value = '';  // по умолчанию пусто
    if (adminForm) adminForm.appendChild(checkoFlag);
  }

  // ===== Вспомогалки =========================================================
  const PLACEHOLDER = 'ФИО скрыто ФНС';
  const RED = '#b00020';

  const getEl = (id) => document.getElementById(id);
  const setIfEmpty = (id, v) => { const el=getEl(id); if (el && !el.value && v!=null) el.value=v; };
  const setChecked = (id, v) => { const el=getEl(id); if (el) el.checked = !!v; };
  const setValue   = (id, v) => { const el=getEl(id); if (el!=null && (el.value==='' || el.value==null)) el.value = (v != null ? v : ''); };

  function computeIsIpFromInn() {
    const v = (innInput.value||'').replace(/\D/g,'');
    return v.length === 12;
  }

  function setRowVisible(fieldName, visible) {
    const input = document.getElementById(`id_${fieldName}`);
    const label = document.querySelector(`label[for="id_${fieldName}"]`);

    let row =
      document.querySelector(`.form-row.field-${fieldName}`) ||
      (input && (input.closest('.form-row') || input.closest('.form-group') || input.closest('.fieldBox') || input.closest('.row'))) ||
      (label && (label.closest('.form-row') || label.closest('.form-group') || label.closest('.fieldBox') || label.closest('.row')));

    if (row) row.style.display = visible ? '' : 'none';
    if (label) {
      const labelWrap = label.closest('div') || label;
      labelWrap.style.display = visible ? '' : 'none';
    }
    if (input) {
      const inputWrap = input.closest('.fieldBox') || input.closest('.form-group') || input.closest('div');
      if (inputWrap) inputWrap.style.display = visible ? '' : 'none';
    }
  }

  function toggleIpMode(isIp) {
    setRowVisible('ceo_post',         !isIp);
    setRowVisible('ceo_record_date',  !isIp);
    setRowVisible('ceo_hidden_by_fns',!isIp);
    setRowVisible('manager_is_org',   !isIp);

    const lbl = document.querySelector('label[for="id_ogrn"]');
    if (lbl) lbl.textContent = isIp ? 'ОГРНИП' : 'ОГРН';

    const kppLbl = document.querySelector('label[for="id_kpp"]');
    if (kppLbl) kppLbl.textContent = isIp ? 'ОКПО' : 'КПП / ОКПО';
  }

  function toRu(d) {
    if (!d) return '';
    const m = d.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!m) return d;
    return `${m[3]}.${m[2]}.${m[1]}`;
  }
  function toIso(d) {
    if (!d) return '';
    const m = d.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (!m) return d;
    return `${m[3]}-${m[2]}-${m[1]}`;
  }
  function beautifyDateField(id) {
    const el = getEl(id);
    if (!el) return;
    if (/^\d{4}-\d{2}-\d{2}$/.test(el.value)) el.value = toRu(el.value);
    el.addEventListener('blur', ()=> { el.value = toRu(toIso(el.value)); });
  }
  function prepareDateForSubmit(id) {
    const el = getEl(id);
    if (el && /^\d{2}\.\d{2}\.\d{4}$/.test(el.value)) el.value = toIso(el.value);
  }

  function ensureNoteBelow(inputEl, noteId) {
    if (!inputEl) return null;
    let note = document.getElementById(noteId);
    if (!note) {
      note = document.createElement('div');
      note.id = noteId; note.className='help'; note.style.marginTop='4px';
      inputEl.parentElement.appendChild(note);
    }
    return note;
  }
  function escapeHtml(s){return (s||'').replace(/[&<>"']/g,m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  function renderWasNote(noteEl, prevText){
    if (!noteEl) return;
    if (prevText && prevText.trim()){
      noteEl.innerHTML = `<span style="opacity:.85;">Было: <em>${escapeHtml(prevText.trim())}</em></span>`;
    } else {
      noteEl.textContent = '';
    }
  }

  function parseKppOkpo(s){
    const raw = (s||'').trim(); if (!raw) return {kpp:'',okpo:''};
    const parts = raw.split('/').map(x=>x.trim());
    let a=parts[0]||'', b=parts[1]||'';
    if (parts.length===1) {
      const only=a.replace(/\D/g,'');
      return (only.length===9) ? {kpp:only,okpo:''} : {kpp:'',okpo:only};
    }
    a=a.replace(/\D/g,''); b=b.replace(/\D/g,'');
    const firstIsKpp=(a.length===9), secondIsKpp=(b.length===9);
    if (firstIsKpp && !secondIsKpp) return {kpp:a,okpo:b};
    if (!firstIsKpp && secondIsKpp) return {kpp:b,okpo:a};
    return {kpp:a,okpo:b};
  }
  function formatKppOkpo({kpp,okpo}){
    const k=(kpp||'').replace(/\D/g,''), o=(okpo||'').replace(/\D/g,'');
    if (k && o) return `${k} / ${o}`; if (k) return k; if (o) return o; return '';
  }

  // === Финпоказатели (inline CounterpartyFinancialYear) =====================

  let FY_INLINE_PREFIX = null;  // определим динамически

  function detectFinancialInlinePrefix() {
    if (FY_INLINE_PREFIX) return FY_INLINE_PREFIX;

    const mgmtInputs = document.querySelectorAll('input[id$="-TOTAL_FORMS"]');
    for (const inp of mgmtInputs) {
      const id = inp.id; // например: id_counterpartyfinancialyear_set-TOTAL_FORMS
      if (!id.startsWith('id_') || !id.endsWith('-TOTAL_FORMS')) continue;
      const prefix = id.slice(3, id.length - '-TOTAL_FORMS'.length);
      // проверяем, есть ли поле year в первой форме
      if (document.getElementById(`id_${prefix}-0-year`)) {
        FY_INLINE_PREFIX = prefix;
        console.log('Detected financial inline prefix:', FY_INLINE_PREFIX);
        return FY_INLINE_PREFIX;
      }
    }
    console.warn('Не удалось определить префикс фин-инлайна');
    return null;
  }

  function fySetValue(prefix, index, fieldName, value) {
    const elId = `id_${prefix}-${index}-${fieldName}`;
    const el = document.getElementById(elId);
    if (!el) return;
    if (el.value !== '' && el.value !== null) return;
    el.value = (value == null ? '' : value);
  }

  /**
   * Заполняем инлайн финансовых показателей:
   *  - для НОВЫХ контрагентов (initialForms == 0);
   *  - не трогаем уже существующие данные, чтобы не плодить дубликаты.
   */
  function fillFinancialYears(financialYears) {
    if (!Array.isArray(financialYears) || !financialYears.length) return;

    const prefix = detectFinancialInlinePrefix();
    if (!prefix) return;

    const totalFormsInput   = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const initialFormsInput = document.getElementById(`id_${prefix}-INITIAL_FORMS`);

    const totalForms   = totalFormsInput   ? parseInt(totalFormsInput.value   || '0', 10) : 0;
    const initialForms = initialFormsInput ? parseInt(initialFormsInput.value || '0', 10) : 0;

    // 🔴 У контрагента уже есть сохранённые финпоказатели — ничего не подставляем
    if (initialForms > 0) {
      console.log('Financial years already exist, skip auto-fill');
      return;
    }

    // Контрагент новый — спокойно заполняем первые extra-формы
    const maxForms = Math.min(totalForms, financialYears.length);

    financialYears.slice(0, maxForms).forEach((fy, idx) => {
      if (!fy || typeof fy.year === 'undefined' || fy.year === null) return;

      fySetValue(prefix, idx, 'year',          fy.year);
      fySetValue(prefix, idx, 'revenue',       fy.revenue);
      fySetValue(prefix, idx, 'net_profit',    fy.net_profit);
      fySetValue(prefix, idx, 'equity',        fy.equity);
      fySetValue(prefix, idx, 'share_capital', fy.share_capital);
      fySetValue(prefix, idx, 'liabilities_long',  fy.liabilities_long);
      fySetValue(prefix, idx, 'liabilities_short', fy.liabilities_short);
      fySetValue(prefix, idx, 'payables',          fy.payables);
      fySetValue(prefix, idx, 'cf_operating',      fy.cf_operating);
    });
  }

  // ===== Примечание под руководителем =======================================
  let ceoPostLine = document.getElementById('ceo-post-line');
  if (ceoInput && !ceoPostLine) {
    ceoPostLine = document.createElement('div');
    ceoPostLine.id='ceo-post-line'; ceoPostLine.className='help'; ceoPostLine.style.marginTop='4px';
    ceoInput.parentElement.appendChild(ceoPostLine);
  }

  function renderCeoNote({ restricted, prevName }) {
    if (!ceoPostLine) return;
    if (restricted) {
      ceoPostLine.innerHTML = '<em style="color:#b00020">ФИО руководителя скрыто ФНС (ограничение доступа)</em>';
      return;
    }
    if (prevName && prevName.trim()) {
      ceoPostLine.innerHTML = `<span style="opacity:.85;">Было: <em>${escapeHtml(prevName.trim())}</em></span>`;
      return;
    }
    ceoPostLine.innerHTML = '';
  }

  function setCeoPlaceholder(){
    if (!ceoInput) return;
    ceoInput.value=PLACEHOLDER; ceoInput.dataset.placeholder='1';
    ceoInput.style.color=RED; ceoInput.style.fontStyle='italic';
  }
  function clearCeoPlaceholderStyling(){
    if (!ceoInput) return;
    delete ceoInput.dataset.placeholder; ceoInput.style.color=''; ceoInput.style.fontStyle='';
  }
  function isPlaceholderActive(){ return !!(ceoInput && ceoInput.dataset.placeholder && ceoInput.value===PLACEHOLDER); }
  function currentCeoValueOrEmpty(){
    if (!ceoInput) return '';
    const v=(ceoInput.value||'').trim(); if (!v) return '';
    return (ceoInput.dataset.placeholder && v===PLACEHOLDER) ? '' : v;
  }

  function renderSavedWasNotes() {
    [{id:'id_website',key:'website'},{id:'id_country',key:'country'},{id:'id_adress',key:'address'},
     {id:'id_region',key:'region'},{id:'id_fullname',key:'fullname'},{id:'id_kpp',key:'kpp'}].forEach(({ id }) => {
      const el = getEl(id); if (!el) return;
      const key = id.replace(/^id_/,'');
      const note = ensureNoteBelow(el, `${id}-was-note`);
      renderWasNote(note, WAS[key] || '');
    });
    renderCeoNote({
      restricted: !!(hiddenFlag && hiddenFlag.checked),
      prevName: WAS['ceo'] || ''
    });
  }

  // старт
  renderSavedWasNotes();
  beautifyDateField('id_ceo_record_date');
  toggleIpMode(computeIsIpFromInn());
  innInput.addEventListener('input', ()=> toggleIpMode(computeIsIpFromInn()));

  if (hiddenFlag && hiddenFlag.checked && ceoInput && !ceoInput.value) setCeoPlaceholder();
  if (hiddenFlag) {
    hiddenFlag.addEventListener('change', () => {
      if (hiddenFlag.checked && ceoInput && !ceoInput.value) setCeoPlaceholder();
      if (!hiddenFlag.checked && ceoInput && ceoInput.value) clearCeoPlaceholderStyling();
      renderCeoNote({ restricted: hiddenFlag.checked, prevName: WAS['ceo'] || '' });
    });
  }
  if (ceoInput) {
    ceoInput.addEventListener('input', () => {
      if (isPlaceholderActive()) clearCeoPlaceholderStyling();
    });
  }
  if (adminForm) {
    adminForm.addEventListener('submit', () => {
      if (isPlaceholderActive()) ceoInput.value='';
      prepareDateForSubmit('id_ceo_record_date');
      syncWas();
    });
  }

  // === Фоллбек для физлица ==================================================
  function handlePhysicalFallback() {
    const note = ensureNoteBelow(innInput, 'inn-lookup-note');
    if (note) {
      note.innerHTML =
        '<span style="color:#6b7280;">' +
        'По данным ФНС организация или ИП не найдены. ' +
        'Предполагается физическое лицо.' +
        '</span>';
    }

    const nameEl      = getEl('id_name');
    const fullnameEl  = getEl('id_fullname');
    const okopfNameEl = getEl('id_okopf_name');
    const okopfCodeEl = getEl('id_okopf_code');
    const ceoEl       = getEl('id_ceo');

    let titled = '';

    if (nameEl) {
      const rawName = (nameEl.value || '').trim();
      if (rawName) {
        titled = rawName
          .toLowerCase()
          .split(/\s+/)
          .map(w => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' ');
      }
    }

    if (fullnameEl && titled) {
      fullnameEl.value = titled;
    }

    if (okopfNameEl && !okopfNameEl.value) {
      okopfNameEl.value = 'Физическое лицо';
    }
    if (okopfCodeEl) {
      okopfCodeEl.value = '';
    }

    if (ceoEl && titled && !ceoEl.value) {
      ceoEl.value = titled;
      clearCeoPlaceholderStyling();
      renderCeoNote({ restricted: false, prevName: WAS['ceo'] || '' });
    }

    toggleIpMode(false);
  }

  // === Кнопка "Заполнить по ИНН" ============================================
  let btn = document.getElementById('fill-by-inn');
  if (!btn) {
    const parent = innInput.parentElement;
    const wrapper = document.createElement('div');
    wrapper.style.display='flex';
    wrapper.style.alignItems='center';
    wrapper.style.gap='8px';
    parent.insertBefore(wrapper, innInput);
    wrapper.appendChild(innInput);
    btn = document.createElement('button');
    btn.type='button'; btn.id='fill-by-inn';
    btn.textContent='📥 Заполнить по ИНН';
    btn.className='btn btn-success'; btn.style.whiteSpace='nowrap';
    wrapper.appendChild(btn);
  }

  btn.addEventListener('click', async () => {
    // каждый новый клик — сбрасываем флаг
    if (checkoFlag) checkoFlag.value = '';

    let inn = (innInput.value||'').replace(/\D/g,'');
    if (!(inn.length===10 || inn.length===12)) {
      const old=btn.textContent; btn.textContent='Некорректный ИНН';
      setTimeout(()=>btn.textContent=old,1200); innInput.focus(); return;
    }

    const old=btn.textContent; btn.disabled=true; btn.textContent='Загрузка…';
    try {
      const params = new URLSearchParams({ inn });
      const url = `/admin/counterparties/counterparty/fill-by-inn/?${params.toString()}`;
      const resp = await fetch(url,{ credentials:'same-origin' });
      const data = await resp.json();

      console.log('fill-by-inn data:', data);
      console.log('financial_years:', data.financial_years);

      if (data.not_found && data.is_physical) {
        handlePhysicalFallback();
        if (checkoFlag) checkoFlag.value = '';
        btn.textContent = 'ИНН не найден (физлицо)';
        setTimeout(() => btn.textContent = old, 2000);
        return;
      }

      if (!resp.ok || data.error) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      toggleIpMode(!!data.is_ip);

      setIfEmpty('id_ogrn',      data.ogrn);
      setIfEmpty('id_taxregime', data.taxregime);

      setIfEmpty('id_okved_code',    data.okved_code);
      setIfEmpty('id_okved_name',    data.okved_name);
      setIfEmpty('id_okved_version', data.okved_version);

      setIfEmpty('id_okopf_code', data.okopf_code);
      setIfEmpty('id_okopf_name', data.okopf_name);

      setChecked('id_risk_disq_persons',        data.risk_disq_persons);
      setChecked('id_risk_mass_directors',      data.risk_mass_directors);
      setChecked('id_risk_mass_founders',       data.risk_mass_founders);
      setChecked('id_risk_illegal_fin',         data.risk_illegal_fin);
      setValue  ('id_risk_illegal_fin_status',  data.risk_illegal_fin_status);
      setChecked('id_risk_sanctions',           data.risk_sanctions);
      setValue  ('id_risk_sanctions_countries', data.risk_sanctions_countries);
      setChecked('id_risk_sanctioned_founder',  data.risk_sanctioned_founder);

      const riskJsonEl = getEl('id_risk_json');
      if (riskJsonEl) {
        try { riskJsonEl.value = JSON.stringify(data.risk_json || {}); }
        catch (_) { riskJsonEl.value = '{}'; }
      }

      [{id:'id_website',key:'website'},{id:'id_country',key:'country'},{id:'id_adress',key:'address'},
       {id:'id_region',key:'region'},{id:'id_fullname',key:'fullname'},{id:'id_kpp',key:'kpp'},
       {id:'id_okopf_name',key:'okopf_name'},].forEach(({ id, key }) => {
        const el = getEl(id); if (!el) return;
        const newRaw = (data[key] ?? '').toString().trim();
        const prevRaw = (el.value || '').trim();

        if (id==='id_kpp') {
          const prev=parseKppOkpo(prevRaw), next=parseKppOkpo(newRaw);
          const kppChanged = prev.kpp!==next.kpp;
          const okpoReplaced = !!prev.okpo && !!next.okpo && prev.okpo!==next.okpo;
          el.value = formatKppOkpo(next);
          const note = ensureNoteBelow(el, `${id}-was-note`);
          if (kppChanged || okpoReplaced){ renderWasNote(note, prevRaw); setWas('kpp', prevRaw); }
          else { renderWasNote(note,''); }
        } else {
          const note = ensureNoteBelow(el, `${id}-was-note`);
          if (!newRaw){ renderWasNote(note,''); return; }
          if (prevRaw !== newRaw){ el.value=newRaw; renderWasNote(note, prevRaw); setWas(id.replace(/^id_/,''),
            prevRaw); }
          else { renderWasNote(note,''); }
        }
      });

      const prevName = currentCeoValueOrEmpty();
      if (hiddenFlag) hiddenFlag.checked = !!data.ceo_restricted;

      if (data.ceo_restricted) {
        if (ceoInput && !ceoInput.value) setCeoPlaceholder();
        renderCeoNote({ restricted:true, prevName:'' });
      } else {
        const newName = (data.ceo_name || data.ceo || '').trim();
        if (newName) {
          if (ceoInput){ ceoInput.value=newName; clearCeoPlaceholderStyling(); }
          if (prevName && prevName!==newName){ setWas('ceo', prevName); }
          renderCeoNote({ restricted:false, prevName: WAS['ceo']||'' });
        } else {
          renderCeoNote({ restricted:false, prevName: WAS['ceo']||'' });
        }
      }

      setIfEmpty('id_ceo_post',        data.ceo_post);
      setIfEmpty('id_ceo_record_date', data.ceo_record_date);
      beautifyDateField('id_ceo_record_date');

      // --- Финансовые показатели (inline) ---
      if (data.financial_years && data.financial_years.length) {
        fillFinancialYears(data.financial_years);
      }

      // ✅ Успешно подтянули данные по ИНН — помечаем
      if (checkoFlag) {
        checkoFlag.value = '1';
      }

      btn.textContent='Заполнено ✔';
      setTimeout(()=>btn.textContent=old,1200);
    } catch(e) {
      console.error('fill-by-inn error:', e);

      if (checkoFlag) checkoFlag.value = '';

      const innDigits = (innInput.value || '').replace(/\D/g, '');
      if (innDigits.length === 12) {
        handlePhysicalFallback();
        btn.textContent = 'ИНН не найден (физлицо)';
        setTimeout(() => btn.textContent = old, 2000);
      } else {
        btn.textContent='Ошибка';
        setTimeout(()=>btn.textContent=old,1200);
      }
    } finally {
      btn.disabled=false; syncWas();
    }
  });
});
