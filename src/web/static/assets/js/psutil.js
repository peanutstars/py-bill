(function() {
  util = {
    flash: function(message, category) {
      console.log(category+'@'+message);
      $('#flash-message').text('');
      if (message && category) {
        var msg_block = '<div class="box '+category+'">'+message+'</div>';
        $("#flash-message").append(msg_block);
      }
    },
    shows: function(shows, hides) {
      this.flash();
      if (hides) {
        for (var i in hides) {
          $(hides[i]).hide();
        }
      }
      for (var i in shows) {
        $(shows[i]).show();
      }
    },
  };
  ajax = {
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
      opts.success = function(resp) {
        // console.log(JSON.stringify(resp));
        if (callback && resp.success) {
          callback(resp.value);
          if (resp.message) {
            util.flash(resp.message, 'success');
          }
        } else if (resp.success == false) {
          var emsg = 'URL@'+opts.type+': '+opts.url;
          emsg += '<br/>Error: ' + resp.message;
          util.flash(emsg, 'danger');
        }
      } ,
      opts.error = function(resp) {
        console.log('Fail\n' + resp.message);
        var emsg = 'Failed(1):' + opts.url;
        emsg += '<br/>' + resp.message;
        util.flash(emsg, 'danger');
      }
      $.ajax(opts);
    },
  };
})();
