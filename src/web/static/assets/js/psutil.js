(function() {
  util = {
    gui: {
      flash: function(message, category) {
        console.log(category+'@'+message);
        $('#flash-message').text('');
        if (message && category) {
          var msg_block = '<div class="box '+category+'">'+message+'</div>';
          $("#flash-message").append(msg_block);
        }
      },
      show: {
        buttons: function(shows, hides) {
          util.gui.flash();
          if (hides) {
            for (var i in hides) {
              $(hides[i]).hide();
            }
          }
          for (var i in shows) {
            $(shows[i]).show();
          }
        },
        area: function(eventId, iconId, areaId) {
          $(eventId).on("click", function(){
            if($(areaId).is(":visible")) {
              $(iconId).removeClass("fa-caret-down").addClass("fa-caret-right");
              $(areaId).hide();
            } else {
              $(iconId).removeClass("fa-caret-right").addClass("fa-caret-down");
              $(areaId).show();
            }
            // util.file.downloadCSV('aaa.csv', '1,2,3,');
          });      
        }
      },
      spot_flash: function(selector, msg, color, duration) {
        let html = '<span style="color: '+color+';">'+msg+'</span>';
        $(selector).html(html);
        if (duration > 0) {
          setTimeout(function(){$(selector).html('')}, duration*1000);
        }
      }
    },
    file: {
      downloadCSV: function (filename, content) {
        if ( window.navigator.msSaveOrOpenBlob && window.Blob ) {
            var blob = new Blob( [ content ], { type: "text/csv;charset=utf-8" } );
            navigator.msSaveOrOpenBlob( blob, filename );
        } else {
            var link = document.createElement('a');
            link.href = 'data:attachment/csv,' +  encodeURIComponent(content);
            link.target = '_blank';
            link.download = filename;
            document.body.appendChild(link);
            link.click();
        }
      },
      query_to_csv: function(filename, title, data) {
        let EOL = '\r\n'
        let csv = '';
        let idx;
        csv += title + (','.repeat(data.colnames.length-1)) + EOL.repeat(2);
        csv += data.colnames.join() + EOL;
        for (idx in data.fields) {
          csv += data.fields[idx].join() + EOL;
        }
        this.downloadCSV(filename, csv);
      },
      sim_data_to_csv: function(filename, title, data) {
        let EOL = '\r\n'
        let csv = '';
        let idx;
        csv += title +(','.repeat(data.colnames.length-1))+ EOL.repeat(2);
        csv += 'Report,"'+JSON.stringify(data.report)+'"'+(','.repeat(data.colnames.length-2))+ EOL;
        csv += 'CFG,"'+JSON.stringify(data.cfg)+'"'+(','.repeat(data.colnames.length-2))+EOL.repeat(2);
        csv += data.colnames.join() + EOL;
        for (idx in data.fields) {
          csv += data.fields[idx].join() + EOL;
        }
        this.downloadCSV(filename, csv);
      },
    },
    formatNumber: function(num) {
      return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,')
    },
    paddingNumber: function(num, length) {
      let s = '0000000000000000'+parseInt(num);
      return s.substr(s.length-length);
    },
    isValidDate: function(dstr) {
      let darr = dstr.split('-').map(function(e){
        return parseInt(e);
      });
      if (darr.length < 3) {
        return false;
      }
      let date = new Date(darr);
      return (date == 'Invalid Date') ? false : true;
    }
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
      var params = {method: 'GET', url: url, datatype: 'json', params: {ids: data.join()}, duration: 30};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.assets);});
    },
    kakao_overseas: function(cb) {
      let url = 'https://stock.kakao.com/api/securities.json';
      let data = ['USA-DJI', 'USA-COMP']
      let params = {method: 'GET', url: url, datatype: 'json', params: {ids: data.join()}, duration: 120};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.recentSecurities);});
    },
    query_all_list: function(cb) {
      ajax.post('/ajax/stock/list', {}, cb);
    },
    query_delete_recent_stock: function(code, cb) {
      ajax.delete('/ajax/stock/item/'+code, {}, cb);
    },
    query_columns: function(code, months, params, cb) {
      ajax.post('/ajax/stock/item/'+code+'/columns/'+months, params, cb);
    },
    query_simulation: function(code, index, params, cb) {
      ajax.post('/ajax/stock/item/'+code+'/simulation/'+index, params, cb);
    },
    query_simulation_chart: function(code, index, params, cb) {
      ajax.post('/ajax/stock/item/'+code+'/simulation-chart/'+index, params, cb);
    },
    query_investors_graph: function(code, months, cb) {
      var params = {
          colnames: ['stamp', 'foreigner', 'institute', 'person', 'shortamount', 'end'],
          accmulator: true
        };
      this.query_columns(code, months, params, cb);
    },
    query_algo_brief: function(code, params, cb) {
      ajax.post('/ajax/stock/item/'+code+'/algo-brief', params, cb);
    },
    query_investors_table: function(code, months, cb) {
      this.query_columns(code, months, {colnames: ['stamp', 'foreigner', 'frate', 'institute', 'person']}, cb);
    },
    query_daily_table: function(code, months, cb) {
      this.query_columns(code, months, {colnames: ['stamp', 'start', 'high', 'low', 'end', 'volume']}, cb);
    },
    query_table: function(code, months, cb) {
      this.query_columns(code, months, {colnames: []}, cb);
    },
    adjust_stock_split: function(code, params, cb){
      ajax.post('/ajax/stock/item/'+code+'/adjust-stock-split', params, cb);
    },
    text_compare_color: function(pprice, price){
      if (pprice > price)
        return 'color-down';
      if (pprice < price)
        return 'color-up';
      return '';
    },
    text_color_ralign: function(num, right) {
      var color = (num > 0) ? 'stock color-up' : ((num < 0) ? 'stock color-down': 'stock');
      return right ? color+' align-right': color;
    },
    has_code: function(code, list) {
      if (code) {
        let short_code = 'A'+util.paddingNumber(code, 6);
        for (var i in list) {
          let item = list[i];
          if (item.short_code == short_code) {
            return true;
          }
        } 
      }
      return false;
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
    put :function(url, params, callback) {
      var opts = {
        dataType : 'json',
        type : 'PUT',
        contentType: "application/json",
        async : true,
        url : url,
        data : JSON.stringify(params),
      };
      this.do_ajax(opts, callback);
    },
    patch :function(url, params, callback) {
      var opts = {
        dataType : 'json',
        type : 'PATCH',
        contentType: "application/json",
        async : true,
        url : url,
        data : JSON.stringify(params),
      };
      this.do_ajax(opts, callback);
    },
    delete :function(url, params, callback) {
      var opts = {
        dataType : 'json',
        type : 'DELETE',
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
            util.gui.flash(resp.message, 'success');
          }
        } else if (resp.success == false) {
          var emsg = 'URL@'+opts.type+': '+opts.url;
          emsg += '<br/>Error: ' + resp.message;
          util.gui.flash(emsg, 'danger');
        }
      } ,
      opts.error = function(resp) {
        console.log('Fail\n' + resp.message);
        var emsg = 'Failed(1):' + opts.url;
        emsg += '<br/>' + resp.message;
        util.gui.flash(emsg, 'danger');
      }
      $.ajax(opts);
    },
  };
  // Sidebar Menu Function
  $(".recent-stock-delete").each(function(idx){
    $(this).on('click', function(){
      stock.query_delete_recent_stock($(this).attr('value'), function(resp){
        // console.log(JSON.stringify(resp));
        $('#menu-field-'+resp.code).remove();
      });
    });
  });
})();
