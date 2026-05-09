var dmcfuncs = window.dashMantineFunctions = window.dashMantineFunctions || {};

dmcfuncs.formatPercent1 = function (value) {
  return value.toFixed(1) + "%";
};

dmcfuncs.formatMoney1 = function (value) {
  return value.toFixed(1) + " M$";
};