var dmcfuncs = window.dashMantineFunctions = window.dashMantineFunctions || {};
var dmc = window.dash_mantine_components;


dmcfuncs.highlightExceptions = function (dateObj, options) {
    // Просто используем dateObj как строку, если он уже в нужном формате
    const dateString = dateObj;
    
    if (options.exceptions && options.exceptions.hasOwnProperty(dateString)) {
        const isWorkingDay = options.exceptions[dateString];
        
        if (isWorkingDay === true) {
            return { style: { color: '#020202ff' } };
        } else if (isWorkingDay === false) {
            return { style: {color: '#ed0b0bff' } };
        }
    }
    
    return {};
}



