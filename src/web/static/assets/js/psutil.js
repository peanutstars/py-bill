(function() {
  util = {
    gui: {
      _flash_tid: null,
      _flashsel: $('#flash-message'),
      flash: function(message, category="danger") {
        console.log(`flash: ${category}@${message}`);
        util.gui._flashsel.html('');
        if (message) {
          util.gui._flashsel.html(`<div class="flash-message box tada animated ${category}"><b>${message}</b></div>`);

          // Calculating the middle position
          $('#flash-message div').css('left', ($(window).width()-$('#flash-message div').width())/2);

          util.flash_hide();
        }
      },
      flash_hide: function() {
        if (util.gui._flash_tid) {
          clearTimeout(util.gui._flash_tid);
        }
        util.gui._flash_tid = setTimeout(() => { util.gui._flashsel.html(''); util.gui._flash_tid=null; }, 2000);
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
      },
      dialog: function(kwargs={}) {
        let s = {
          dialog:  $("#dialog-box"),
          title:   $("#dialog-box-title"),
          message: $("#dialog-box-content"),
          yes:     $("#dialog-box-yes"),
          no:      $("#dialog-box-no"),
          okay:    $("#dialog-box-okay"),
        };
        let _close = () => {s.dialog.hide();};
        let _click = (e) => { _close(); if('data' in e){e.data();} }

        if ('title' in kwargs)   { s.title.text(kwargs.title) }
        if ('message' in kwargs) { s.message.html(kwargs.message.replace(/(?:\r\n|\r|\n)/g, '<br>')); }
        if ('no' in kwargs && kwargs.no) {
          s.no.off('click');
          s.no.on('click', 'cb_no' in kwargs ? kwargs.cb_no : null, _click);
          s.no.show();
        }
        if ('yes' in kwargs && kwargs.yes) {
          s.yes.off('click');
          s.yes.on('click', 'cb_yes' in kwargs ? kwargs.cb_yes : null, _click);
          s.yes.show();
        }
        if ('okay' in kwargs && kwargs.okay) {
          s.okay.off('click');
          s.okay.on('click', 'cb_okay' in kwargs ? kwargs.cb_okay : null, _click);
          s.okay.show();
        }
        s.dialog.show();
      },
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
    kakao: "stockplus.com",
    kakao_brief_stock: function(code, cb) {
      var url = 'https://'+this.kakao+'/api/securities/KOREA-A'+code+'.json';
      var params = {method: 'GET', url: url, datatype: 'json', duration: 90};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.recentSecurity);});
    },
    kakao_brief_company: function(code, cb) {
      var url = 'https://'+this.kakao+'/api/companies/KOREA-A'+code+'.json';
      var params = {method: 'GET', url: url, datatype: 'json', duration: 3600};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.company);});
    },
    kakao_assets: function(codes, cb) {
      var url = 'https://'+this.kakao+'/api/assets.json';
      var data = codes.map(function(el){return 'KOREA-A'+el});
      var params = {method: 'GET', url: url, datatype: 'json', params: {ids: data.join()}, duration: 30};
      ajax.post('/ajax/proxy', params, function(resp){cb(resp.assets);});
    },
    kakao_overseas: function(cb) {
      let url = 'https://'+this.kakao+'/api/securities.json';
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
    query_algo_index_mark: function(code, index, cb){
      ajax.post('/ajax/stock/item/'+code+'/algo-index-mark/'+index, {}, cb);
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
          // console.log('ajax', resp);
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
  // Flash-message
  util.gui.flash_hide();
})();
