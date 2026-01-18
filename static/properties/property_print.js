// static/properties/property_print.js

function formatCurrency(value) {
  var num = Number(value) || 0;
  return num.toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';
}

function formatNumber(value) {
  var num = Number(value) || 0;
  return num.toLocaleString('ru-RU', { maximumFractionDigits: 0 });
}

function formatDeltaCompact(delta) {
  var num = Number(delta) || 0;
  if (num === 0) return '0 ₽';

  var sign = num < 0 ? '-' : '+';
  var v = Math.abs(num);
  var unit = '';
  var base = v;

  if (v >= 1000000000) {
    base = v / 1000000000;
    unit = ' млрд ₽';
  } else if (v >= 1000000) {
    base = v / 1000000;
    unit = ' млн ₽';
  } else if (v >= 1000) {
    base = v / 1000;
    unit = ' тыс. ₽';
  } else {
    return sign + v.toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ₽';
  }

  return sign + base.toFixed(1).replace('.', ',') + unit;
}

// --- форматирование валют и чисел ---
(function () {
  document.querySelectorAll('.js-currency').forEach(function (el) {
    var raw = el.dataset.value;
    var prefix = el.dataset.prefix || '';
    el.textContent = prefix + formatCurrency(raw);
  });

  document.querySelectorAll('.js-number').forEach(function (el) {
    var raw = el.dataset.value;
    el.textContent = formatNumber(raw);
  });
})();


// --- графики динамики оценки (timeline) — для всех таблиц ---
// Работает и с .valuation-timeline-table (печатные карточки),
// и с .table-timeline-total (страница аналитики)
(function () {
  var tables = document.querySelectorAll('.valuation-timeline-table, .table-timeline-total');
  if (!tables.length) return;

  tables.forEach(function (table) {
    var cells = Array.from(table.querySelectorAll('td.timeline-total'));
    if (!cells.length) return;

    var values = cells.map(function (c) {
      return parseFloat(c.dataset.value || '0') || 0;
    });

    var max = Math.max.apply(null, values) || 0;

    cells.forEach(function (cell, idx) {
      var val = values[idx];
      var pct = max ? (val / max) * 100 : 0;

      var mainLabel = formatCurrency(val);
      var deltaLabelHtml = '';

      if (idx > 0) {
        var prevVal = values[idx - 1];
        if (prevVal) {
          var delta = val - prevVal;
          var deltaPct = (delta / prevVal) * 100;
          if (delta !== 0) {
            var deltaClass = delta > 0 ? 'delta-up' : 'delta-down';
            deltaLabelHtml =
              '<span class="metric-delta ' + deltaClass + '">' +
                formatDeltaCompact(delta) +
                ' (' + deltaPct.toFixed(1).replace('.', ',') + '%)' +
              '</span>';
          }
        }
      }

      var labelHtml =
        '<span class="metric-main">' + mainLabel + '</span>' +
        (deltaLabelHtml ? ' ' + deltaLabelHtml : '');

      cell.innerHTML =
        '<div class="metric-bar">' +
          '<div class="metric-bar-fill" style="width:' + pct.toFixed(0) + '%"></div>' +
          '<span class="metric-bar-label">' + labelHtml + '</span>' +
        '</div>';
    });
  });
})();


// --- сравнение рыночной и кадастровой — для всех таблиц (карточки) ---
(function () {
  var tables = document.querySelectorAll('.comparison-table');
  if (!tables.length) return;

  tables.forEach(function (table) {
    // если это таблица сравнения на странице аналитики по объекту —
    // для неё отдельная логика ниже, тут обрабатываем только статические
    if (table.id === 'object-comparison-table') return;

    var rows = Array.from(table.querySelectorAll('tr[data-type]'));
    if (!rows.length) return;

    var data = {};
    var values = [];

    rows.forEach(function (row) {
      var type = row.getAttribute('data-type');
      var cell = row.querySelector('td.comparison-cell');
      if (!cell) return;
      var val = parseFloat((cell.dataset.value || '0').replace(' ', '')) || 0;
      data[type] = { row: row, cell: cell, value: val };
      values.push(val);
    });

    if (!values.length) return;
    var max = Math.max.apply(null, values) || 1;

    rows.forEach(function (row) {
      var type = row.getAttribute('data-type');
      var obj = data[type];
      if (!obj) return;

      var pct = (obj.value / max) * 100;
      var mainLabel = formatCurrency(obj.value);
      var extraLabel = '';

      if (type === 'valuation' && data['kadastr'] && data['kadastr'].value > 0) {
        var ratio = obj.value / data['kadastr'].value;
        extraLabel = '· ' + ratio.toFixed(2).replace('.', ',') + ' ×';
      }

      obj.cell.innerHTML =
        '<div class="metric-bar">' +
          '<div class="metric-bar-fill" style="width:' + pct.toFixed(0) + '%"></div>' +
          '<span class="metric-bar-label">' +
            '<span class="metric-main">' + mainLabel + '</span>' +
            (extraLabel ? '<span class="metric-delta">' + extraLabel + '</span>' : '') +
          '</span>' +
        '</div>';
    });
  });
})();


// --- Универсальный график РС / КС (используем в аналитике по объекту) ---
window.renderValuationVsKadastrChart = function (chartId, data) {
  if (!data) return;
  if (typeof Plotly === 'undefined') return;

  var el = document.getElementById(chartId);
  if (!el) return;

  var labels    = data.labels || [];
  var valuation = data.valuation || [];
  var kadastr   = data.kadastr || [];
  var ratio     = data.ratio || [];

  // Стоимость в млн ₽
  var valuationM = valuation.map(function (v) { return (v || 0) / 1e6; });
  var kadastrM   = kadastr.map(function (v) { return (v || 0) / 1e6; });

  var valText = valuationM.map(function (v) { return v.toFixed(1); });
  var kadText = kadastrM.map(function (v) { return v.toFixed(1); });

  var traceVal = {
    x: labels,
    y: valuationM,
    type: "bar",
    name: "Рыночная стоимость",
    marker: { color: "#3b82f6" },
    yaxis: "y1",
    text: valText,
    textposition: "inside",
    insidetextanchor: "end",
    textfont: { size: 9, color: "#ffffff" },
  };

  var traceKad = {
    x: labels,
    y: kadastrM,
    type: "bar",
    name: "Кадастровая стоимость",
    marker: { color: "#9ca3af" },
    yaxis: "y1",
    text: kadText,
    textposition: "inside",
    insidetextanchor: "end",
    textfont: { size: 9, color: "#111827" },
  };

  var traceRatio = {
    x: labels,
    y: ratio,
    type: "scatter",
    mode: "lines+markers+text",
    name: "РС / КС",
    yaxis: "y2",
    line: { shape: "spline", color: "#16a34a" },
    marker: { size: 6, color: "#16a34a" },
    text: ratio.map(function (r) { return (r || 0).toFixed(2) + "×"; }),
    textposition: "top center",
    textfont: { size: 8 },
    cliponaxis: false,
  };

  var layout = {
    barmode: "group",
    margin: { l: 70, r: 70, t: 10, b: 70 },
    legend: { orientation: "h", y: -0.3 },
    yaxis: {
      title: "Стоимость, млн ₽",
      tickformat: ",.1f",
      rangemode: "tozero",
    },
    yaxis2: {
      title: "РС / КС, ×",
      overlaying: "y",
      side: "right",
      rangemode: "tozero",
    },
    xaxis: {
      tickangle: -45,
    },
  };

  var config = {
    displayModeBar: false,
    responsive: true,
  };

  Plotly.newPlot(el, [traceVal, traceKad, traceRatio], layout, config);
};


// --- Динамика по отдельному объекту + таблица оценок + кадастр (страница аналитики) ---
(function () {
  var dataScript = document.getElementById('valuations-series-data');
  if (!dataScript) return;

  var series;
  try {
    series = JSON.parse(dataScript.textContent);
  } catch (e) {
    console.error('Ошибка парсинга valuations_series', e);
    return;
  }

  if (!Array.isArray(series) || !series.length) return;

  // kadastr_series (полная история кадастровой стоимости)
  var kadastrScript = document.getElementById('kadastr-series-data');
  var kadastrSeries = [];
  if (kadastrScript) {
    try {
      kadastrSeries = JSON.parse(kadastrScript.textContent) || [];
    } catch (e) {
      console.error('Ошибка парсинга kadastr_series', e);
      kadastrSeries = [];
    }
  }

  function findKadastrItem(pid) {
    if (!Array.isArray(kadastrSeries)) return null;
    return kadastrSeries.find(function (s) { return s.id === pid; }) || null;
  }

  var selectEl        = document.getElementById('property-select');
  var summaryEl       = document.getElementById('property-summary');
  var timelineBody    = document.querySelector('#object-timeline-table tbody');
  var detailBody      = document.querySelector('#object-valuations-table tbody');
  var kadastrBody     = document.querySelector('#object-kadastr-table tbody');
  var comparisonTable = document.getElementById('object-comparison-table');
  var comparisonNote  = document.getElementById('object-comparison-note');
  var chartEl         = document.getElementById('object-valuation-kadastr-chart');

  if (!selectEl || !summaryEl || !timelineBody || !detailBody || !kadastrBody) return;

  function renderPlaceholder() {
    timelineBody.innerHTML =
      '<tr>' +
        '<td colspan="2" class="cell-muted" style="text-align:center;">' +
          'Выберите объект в списке выше, чтобы увидеть его историю оценок.' +
        '</td>' +
      '</tr>';

    detailBody.innerHTML =
      '<tr>' +
        '<td colspan="5" class="cell-muted" style="text-align:center;">' +
          'Выберите объект в списке выше, чтобы увидеть список его оценок.' +
        '</td>' +
      '</tr>';

    kadastrBody.innerHTML =
      '<tr>' +
        '<td colspan="2" class="cell-muted" style="text-align:center;">' +
          'Выберите объект в списке выше, чтобы увидеть историю кадастровой стоимости.' +
        '</td>' +
      '</tr>';

    if (comparisonTable && comparisonNote) {
      var cells = comparisonTable.querySelectorAll('td.comparison-cell');
      cells.forEach(function (c) { c.textContent = '—'; });
      comparisonNote.textContent =
        'Выберите объект, чтобы увидеть сравнение рыночной и кадастровой стоимости.';
    }

    if (chartEl) {
      chartEl.innerHTML = '';
    }

    summaryEl.innerHTML =
      '<span class="property-summary-placeholder">Пока объект не выбран.</span>';
  }

  function renderSeries(propertyId) {
    if (!propertyId) {
      renderPlaceholder();
      return;
    }

    var pid = parseInt(propertyId, 10);
    var item = series.find(function (s) { return s.id === pid; });
    if (!item || !Array.isArray(item.points) || !item.points.length) {
      timelineBody.innerHTML =
        '<tr><td colspan="2" class="cell-muted" style="text-align:center;">' +
        'Нет данных по оценкам для выбранного объекта.' +
        '</td></tr>';

      detailBody.innerHTML =
        '<tr><td colspan="5" class="cell-muted" style="text-align:center;">' +
        'Нет сохранённых оценок по объекту.' +
        '</td></tr>';

      kadastrBody.innerHTML =
        '<tr><td colspan="2" class="cell-muted" style="text-align:center;">' +
        'Нет данных о кадастровой стоимости по выбранному объекту.' +
        '</td></tr>';

      if (comparisonTable && comparisonNote) {
        var cells = comparisonTable.querySelectorAll('td.comparison-cell');
        cells.forEach(function (c) { c.textContent = '—'; });
        comparisonNote.textContent =
          'Нет достаточных данных для сравнения рыночной и кадастровой стоимости.';
      }

      if (chartEl) chartEl.innerHTML = '';

      summaryEl.innerHTML =
        '<span class="property-summary-placeholder">Нет данных по оценкам.</span>';
      return;
    }

    // сортируем оценки по дате (по возрастанию)
    var points = item.points.slice().sort(function (a, b) {
      return new Date(a.date) - new Date(b.date);
    });

    // считаем max и дельты
    var max = 0;
    points.forEach(function (p, idx) {
      p._val = parseFloat(p.amount) || 0;
      if (p._val > max) max = p._val;

      if (idx > 0) {
        var prev = points[idx - 1];
        var prevVal = prev._val || 0;
        if (prevVal !== 0) {
          var delta = p._val - prevVal;
          var deltaPct = (delta / prevVal) * 100;
          p._delta = delta;
          p._deltaPct = deltaPct;
        } else {
          p._delta = 0;
          p._deltaPct = null;
        }
      } else {
        p._delta = null;
        p._deltaPct = null;
      }
    });

    // --- 1. Таймлайн по объекту ---
    var timelineRowsHtml = points.map(function (p, idx) {
      var val = p._val;
      var pctWidth = max ? (val / max) * 100 : 0;
      var dateStr = new Date(p.date).toLocaleDateString('ru-RU');

      var mainLabel = formatCurrency(val);
      var deltaLabelHtml = '';

      if (idx > 0 && p._delta !== null && p._delta !== 0) {
        var deltaClass = p._delta > 0 ? 'delta-up' : 'delta-down';
        deltaLabelHtml =
          '<span class="metric-delta ' + deltaClass + '">' +
            formatDeltaCompact(p._delta) +
            (p._deltaPct !== null
              ? ' (' + p._deltaPct.toFixed(1).replace('.', ',') + '%)'
              : '') +
          '</span>';
      }

      var labelHtml =
        '<span class="metric-main">' + mainLabel + '</span>' +
        (deltaLabelHtml ? ' ' + deltaLabelHtml : '');

      return (
        '<tr>' +
          '<td class="cell-muted">' + dateStr + '</td>' +
          '<td>' +
            '<div class="metric-bar">' +
              '<div class="metric-bar-fill" style="width:' + pctWidth.toFixed(0) + '%"></div>' +
              '<span class="metric-bar-label">' + labelHtml + '</span>' +
            '</div>' +
          '</td>' +
        '</tr>'
      );
    }).join('');

    timelineBody.innerHTML = timelineRowsHtml;

    // --- 2. Таблица оценок "как в карточке объекта" ---
    var detailRowsHtml = points.slice().reverse().map(function (p) {
      var dateStr = new Date(p.date).toLocaleDateString('ru-RU');
      var deltaHtml = '';

      if (p._delta !== null && p._delta !== 0) {
        var deltaClass = p._delta > 0 ? 'delta-up' : 'delta-down';
        var arrow = p._delta > 0 ? '▲ ' : '▼ ';
        var deltaText = formatDeltaCompact(p._delta);
        var deltaPctText = (p._deltaPct !== null
          ? ' (' + p._deltaPct.toFixed(1).replace('.', ',') + '%)'
          : '');
        deltaHtml =
          '<div class="' + deltaClass + '">' +
            arrow + deltaText + deltaPctText +
          '</div>';
      } else if (p._delta === 0) {
        deltaHtml = '<div class="delta-flat">■ 0 ₽</div>';
      }

      // Федресурс
      var fedresHtml = '—';
      if (p.rights_description) {
        var shareText = p.share || 'Сообщение Федресурса';
        fedresHtml =
          '<a href="' + p.rights_description + '" class="fedres-link" target="_blank" rel="noopener">' +
            '<span class="fedres-icon">⧉</span>' +
            '<span class="fedres-text">' + shareText + '</span>' +
          '</a>';
      } else if (p.share) {
        fedresHtml = p.share;
      }

      // Отчёт
      var reportTextNum = p.report_number || '—';
      var reportDateStr = '';
      if (p.report_date) {
        var d = new Date(p.report_date);
        if (!isNaN(d)) {
          reportDateStr = d.toLocaleDateString('ru-RU');
        }
      }
      var reportHtml;
      if (p.report_url) {
        reportHtml =
          '<a href="' + p.report_url + '" class="cell-link" target="_blank" rel="noopener">' +
            '№' + reportTextNum +
          '</a>' +
          (reportDateStr ? ' от ' + reportDateStr : '');
      } else {
        if (p.report_number || p.report_date) {
          reportHtml =
            '№' + reportTextNum +
            (reportDateStr ? ' от ' + reportDateStr : '');
        } else {
          reportHtml = '—';
        }
      }

      var appraiser = p.appraiser || '—';

      return (
        '<tr>' +
          '<td class="col-date">' + dateStr + '</td>' +
          '<td class="col-sum">' +
            '<div>' + formatCurrency(p._val) + '</div>' +
            (deltaHtml || '') +
          '</td>' +
          '<td class="col-fedres">' + fedresHtml + '</td>' +
          '<td class="col-report">' + reportHtml + '</td>' +
          '<td class="col-appraiser">' + appraiser + '</td>' +
        '</tr>'
      );
    }).join('');

    detailBody.innerHTML = detailRowsHtml;

    // --- 3. История кадастровой стоимости ---
    var kItem = findKadastrItem(pid);
    if (!kItem || !Array.isArray(kItem.points) || !kItem.points.length) {
      kadastrBody.innerHTML =
        '<tr><td colspan="2" class="cell-muted" style="text-align:center;">' +
          'Нет данных о кадастровой стоимости по выбранному объекту.' +
        '</td></tr>';
    } else {
      var kPointsSorted = kItem.points
        .slice()
        .sort(function (a, b) { return new Date(a.date) - new Date(b.date); });

      var kRowsHtml = kPointsSorted.map(function (p) {
          var dateStr = new Date(p.date).toLocaleDateString('ru-RU');
          var val = parseFloat(p.amount) || 0;
          return (
            '<tr>' +
              '<td class="col-date">' + dateStr + '</td>' +
              '<td class="col-sum">' + formatCurrency(val) + '</td>' +
            '</tr>'
          );
        }).join('');

      kadastrBody.innerHTML = kRowsHtml;
    }

    // --- 4. Summary-блок под селектом (последняя рыночная + изменение) ---
    var last = points[points.length - 1];
    var prev = points.length > 1 ? points[points.length - 2] : null;

    var lastVal = last._val || 0;
    var lastDateStr = new Date(last.date).toLocaleDateString('ru-RU');

    var summaryHtml =
      'Последняя оценка: ' +
      '<span class="value">' + formatCurrency(lastVal) + '</span>' +
      ' от ' + lastDateStr + '.';

    if (prev) {
      var prevVal2 = prev._val || 0;
      var delta2 = lastVal - prevVal2;
      var deltaPct2 = prevVal2 ? (delta2 / prevVal2) * 100 : null;
      var deltaClass2 = delta2 > 0 ? 'delta-up' : (delta2 < 0 ? 'delta-down' : '');

      if (delta2 !== 0) {
        var arrow2 = delta2 > 0 ? '▲ ' : '▼ ';
        summaryHtml +=
          ' Изменение к предыдущей оценке: ' +
          '<span class="' + deltaClass2 + '">' +
            arrow2 + formatDeltaCompact(delta2) +
            (deltaPct2 !== null ? ' (' + deltaPct2.toFixed(1).replace('.', ',') + '%)' : '') +
          '</span>.';
      } else {
        summaryHtml += ' Изменение к предыдущей оценке: без изменений.';
      }

      summaryHtml +=
        ' Всего оценок по объекту: <span class="value">' +
        points.length +
        '</span>.';
    } else {
      summaryHtml +=
        ' Это единственная оценка по объекту (истории изменения стоимости пока нет).';
    }

    summaryEl.innerHTML = summaryHtml;

    // --- 5. Сравнение последней рыночной и кадастровой стоимости ---
    if (comparisonTable && comparisonNote) {
      var valCell = comparisonTable.querySelector('tr[data-type="valuation"] td.comparison-cell');
      var kadCell = comparisonTable.querySelector('tr[data-type="kadastr"] td.comparison-cell');

      var kadastrAmountRaw = item.last_kadastr_amount;
      var kadastrAmount = (kadastrAmountRaw != null)
        ? parseFloat(kadastrAmountRaw)
        : null;

      if (!valCell || !kadCell) {
        comparisonNote.textContent =
          'Техническая ошибка при отрисовке сравнения стоимости.';
        return;
      }

      if (!lastVal && !kadastrAmount) {
        valCell.textContent = '—';
        kadCell.textContent = '—';
        comparisonNote.textContent =
          'Нет данных по последней рыночной и кадастровой стоимости.';
      } else if (!lastVal && kadastrAmount) {
        valCell.textContent = '—';
        kadCell.innerHTML =
          '<div class="metric-bar">' +
            '<div class="metric-bar-fill" style="width:100%"></div>' +
            '<span class="metric-bar-label">' +
              '<span class="metric-main">' + formatCurrency(kadastrAmount) + '</span>' +
            '</span>' +
          '</div>';
        comparisonNote.textContent =
          'Нет данных по последней рыночной оценке для сравнения.';
      } else if (lastVal && !kadastrAmount) {
        valCell.innerHTML =
          '<div class="metric-bar">' +
            '<div class="metric-bar-fill" style="width:100%"></div>' +
            '<span class="metric-bar-label">' +
              '<span class="metric-main">' + formatCurrency(lastVal) + '</span>' +
            '</span>' +
          '</div>';
        kadCell.textContent = '—';
        comparisonNote.textContent =
          'Кадастровая стоимость для выбранного объекта не заполнена.';
      } else {
        // есть и рыночная, и кадастровая — строим два бара
        var maxVal = Math.max(lastVal, kadastrAmount);

        function makeBar(value) {
          var pct = maxVal ? (value / maxVal) * 100 : 0;
          return (
            '<div class="metric-bar">' +
              '<div class="metric-bar-fill" style="width:' + pct.toFixed(0) + '%"></div>' +
              '<span class="metric-bar-label">' +
                '<span class="metric-main">' + formatCurrency(value) + '</span>' +
              '</span>' +
            '</div>'
          );
        }

        valCell.innerHTML = makeBar(lastVal);
        kadCell.innerHTML = makeBar(kadastrAmount);

        var ratio = lastVal / kadastrAmount;
        comparisonNote.innerHTML =
          'Соотношение рыночной и кадастровой: <strong>' +
          ratio.toFixed(2).replace('.', ',') +
          ' ×</strong>.';
      }
    }

    // --- 6. График РС / КС по датам для выбранного объекта (аналитика) ---
    if (chartEl && window.renderValuationVsKadastrChart) {
      var chartData = null;

      var kItemForChart = findKadastrItem(pid);
      if (kItemForChart && Array.isArray(kItemForChart.points) && kItemForChart.points.length) {
        // сортируем кадастровые
        var kSorted = kItemForChart.points.slice().sort(function (a, b) {
          return new Date(a.date) - new Date(b.date);
        });

        var labels = [];
        var valArr = [];
        var kadArr = [];
        var ratioArr = [];

        var kIdx = 0;
        var currentK = null;

        points.forEach(function (p) {
          var vDate = new Date(p.date);

          while (kIdx < kSorted.length && new Date(kSorted[kIdx].date) <= vDate) {
            currentK = kSorted[kIdx];
            kIdx += 1;
          }

          if (!currentK || currentK.amount == null) return;

          var valAmount = parseFloat(p.amount) || 0;
          var kadAmount = parseFloat(currentK.amount) || 0;
          if (!kadAmount || kadAmount <= 0) return;

          labels.push(vDate.toLocaleDateString('ru-RU'));
          valArr.push(valAmount);
          kadArr.push(kadAmount);
          ratioArr.push(valAmount / kadAmount);
        });

        if (labels.length) {
          chartData = {
            labels: labels,
            valuation: valArr,
            kadastr: kadArr,
            ratio: ratioArr
          };
        }
      }

      if (chartData) {
        window.renderValuationVsKadastrChart('object-valuation-kadastr-chart', chartData);
      } else {
        chartEl.innerHTML = '';
      }
    }
  }

  selectEl.addEventListener('change', function (e) {
    renderSeries(e.target.value);
  });

  renderPlaceholder();
})();
