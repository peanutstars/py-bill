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
    formatNumber: function(num) {
      return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,')
    },
  };
  stock = {
    kakao_brief_stock: function(code, cb) {
      var url = 'https://stock.kakao.com/api/securities/KOREA-A'+code+'.json';
      var params = {method: 'GET', url: url, datatype: 'json', duration: 90};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.recentSecurity);});
    },
    kakao_brief_company: function(code, cb) {
      var url = 'https://stock.kakao.com/api/companies/KOREA-A'+code+'.json';
      var params = {method: 'GET', url: url, datatype: 'json', duration: 3600};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.company);});
    },
    kakao_assets: function(codes, cb) {
      var url = 'https://stock.kakao.com/api/assets.json';
      var data = codes.map(function(el){return 'KOREA-A'+el});
      var params = {method: 'GET', url: url, datatype: 'json', params: {ids: data.join()}, duration: 90};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.assets);});
    },
    query_columns: function(code, months, params, cb) {
      ajax.post('/ajax/stock/item/'+code+'/columns/'+months, params, cb);
    },
    query_investors_graph: function(code, months, cb) {
      var params = {
          colnames: ['stamp', 'foreigner', 'institute', 'person', 'shortamount', 'end'],
          accmulator: true
        };
      this.query_columns(code, months, params, cb);
    },
    query_investors_table: function(code, months, cb) {
      this.query_columns(code, months, {colnames: ['stamp', 'foreigner', 'frate', 'institute', 'person']}, cb);
    },
    query_daily_table: function(code, months, cb) {
      this.query_columns(code, months, {colnames: ['stamp', 'start', 'high', 'low', 'end', 'volume']}, cb);
    },
    text_color: function(pprice, price){
      if (pprice > price)
        return 'color-down';
      if (pprice < price)
        return 'color-up';
      return '';
    }
  },
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
