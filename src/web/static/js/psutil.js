var util = {
  flash: function(message, category) {
    var msg_block = '<div class="alert alert-'+category+'">'+message+'</div>';
    $("#body-container").append(msg_block);
  },
};

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
                var emsg = 'URL@'+opts.type+': '+opts.url;
                emsg += '<br/>Error: ' + response.errmsg;
                util.flash(emsg, 'danger');
            }
        } ,
        opts.error = function(response) {
            console.log('Fail\n' + response.errorMsg);
            var emsg = 'Failed(1):' + opts.url;
            emsg += '<br/>' + response.errorMsg;
            util.flash(emsg, 'danger');
        }
        $.ajax(opts);
    },
};
