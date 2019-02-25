var ajax = {
    get : function(url, params, callback) {
        var opts = {
            dataType : 'json',
            type : 'GET',
            async : true,
            contentType: "application/json",
            url : url,
            data : JSON.stringify(params),
        };
        this.do_ajax(opts, callback);
    },
    post :function(url, params, callback) {
        var opts = {
            dataType : 'json',
            type : 'POST',
            contentType: "application/json",
            async : true,
            url : url,
            data : JSON.stringify(params),
        };
        this.do_ajax(opts, callback);
    },
    do_ajax : function(opts, callback) {
        opts.success = function(response) {
            if (callback && response.success) {
                callback(response.value);
            } else if (response.success == false) {
                var emsg = 'URL: ' + opts.url ;
                emsg += '\nError: ' + response.errmsg ;
                console.log(emsg) ;
            }
        } ,
        opts.error = function(response) {
            console.log('Fail\n' + response.errorMsg);
            var emsg = 'Failed(1):' + opts.url;
            emsg += '\n\n' + response.errorMsg;
            alert(emsg);
        }
        $.ajax(opts);
    },
}
