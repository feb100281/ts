// здесь пишем всю жабу для dash

var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

dagfuncs.sizeOptions = function (params) {
    return {
        values: params.data.size_options || []
    };
};