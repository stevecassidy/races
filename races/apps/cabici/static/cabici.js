function formatnames(data, title) {
    var val = "";
    if (typeof(data) != 'undefined') {
        val += "<dt>" + title + "</dt><dd>"
        for(var i=0; i<data.length; i++) {
            val += data[i].name;
            if (i<data.length-1) {
                val += ", ";
            }
        }
        val += "</dd>";
    } else {
        val += "<dt>" + title + "</dt><dd>Unknown</dd>";
    }
    return(val);
};

function deletemodalbutton(race) {
    var val = "<div><a href='#' title='Delete Race' data-toggle='modal' data-target='#raceDeleteModal' data-raceurl='" + race.url + "' data-racename='" + race.title +"'><span aria-hidden='true' class='glyphicon glyphicon-trash'></span></a></div>";
    return(val);
}

function addpeoplemodalbutton(race) {
    var val = "<div><a href='#' title='Add Officials' data-toggle='modal' data-target='#addPeopleModal' data-raceurl='" + race.url + "' data-raceid='" + race.id + "' data-racename='" + race.date + ", " + race.location.name + "'><span aria-hidden='true' class='glyphicon glyphicon-user'></span></a></div>";
    return(val);
}

function editmodalbutton(race) {
    var val = "<div><a href='#' data-toggle='modal' data-target='#raceEditModal' title='Edit Race' data-clubslug='" + race.club.slug + "' data-raceurl='" + race.url + "' data-raceid='" + race.id + "' data-racename='" + race.date + ", " + race.location.name + "><span aria-hidden='true' class='glyphicon glyphicon-pencil'></span></a></div>";
    return(val);
}


function populate_race_table(clubslug, auth, manage_members) {

    var edit_column = { data: "id",
                          render: function(data, type, row) {
                              var val = "";
                              val += editmodalbutton(row);
                              val += deletemodalbutton(row);
                              if (manage_members=='True') {
                                  val += addpeoplemodalbutton(row);
                              }
                              return(val);
                          }
                      };

    var columns = [{
                       data: "date",
                       render: function(data, type, row) {
                           var val = "<p>";
                           dd = new Date(data);
                           dd = dd.toGMTString() /* Use GMT because dates in that TZ by default */
                           dd = dd.substring(0,dd.length-12);
                           val += "<b>" +dd + "</b><br>";
                           val += "Sign On: " + row['signontime'].substring(0,5) + "<br>";
                           val += "Start: " + row['starttime'] + "<br>";
                           val += "</p>";
                           return val;
                    }
                },
                { data: "title",
                  render: function(data, type, row) {
                      var val = "<a href='/races/" + row['club']['slug'] + "/" + row['id'] + "'>" + data + "</a>";
                      return val;
                  }},
                { data: "location.name",
                  render: function(data, type, row) {
                      var val = "<div>";
                      val += "<span class='racelocation'>" + data + "</span><br>";
                      val += "<div class='racesuppinfo'>" + row['category'].display + "<br>";
                      val += "Discipline: " + row['discipline'].display + "<br>";
                      val += "Licence: " + row['licencereq'].display + "</div>";
                      val += "</div>";
                      return val;
                  }}
              ]

    if (manage_members == 'True') {
            columns.push({ data: "officials",
                  render: function(data, type, row) {
                      var val = "<dl class='dl-horizontal'>";
                      val += formatnames(data.Commissaire, "Commissaire");
                      val += formatnames(data['Duty Officer'], "Duty Officer");
                      val += formatnames(data['Duty Helper'], "Duty Helper");
                      val += "</dl>";
                      return val;
                  }
              });
    }

    if (auth) {
        columns.push(edit_column);
    }

    $('#racetable').DataTable( {
        processing: true,
        destroy: true,
        ajax: {
                    url: "/api/races/?club="+ clubslug +"&select=future",
                    dataSrc: ''
                },
        paging: false,
        ordering: false,
        rowId: 'id',
        columns: columns,
        fnCreatedRow: function( nRow, aData, iDataIndex ) {
             $(nRow).addClass('status'+aData['status']);
        }
    } );
};

/* populate the table of just the race officials for bulk editing */
function populate_race_official_table(clubslug, auth) {

    var columns = [{
                       data: "date",
                       render: function(data, type, row) {
                           var val = "<p>";
                           dd = new Date(data);
                           dd = dd.toGMTString() /* Use GMT because dates in that TZ by default */
                           dd = dd.substring(0,dd.length-12);
                           val += "<b>" +dd + "</b></p>";
                           return val;
                    }
                },
                { data: "location.name"},
                { data: "commissaire",
                  render: function(data, type, row) {
                      var val = "<dl class='dl-horizontal'>";
                      val += formatnames(data.Commissaire, "Commissaire");
                      val += formatnames(data['Duty Officer'], "Duty Officer");
                      val += formatnames(data['Duty Helper'], "Duty Helper");
                      val += "</dl>";
                      return val;
                  }
                }]


    $('#racetable').DataTable( {
        processing: true,
        destroy: true,
        ajax: {
                    url: "/api/races/?club="+ clubslug +"&select=future",
                    dataSrc: ''
                },
        paging: false,
        ordering: false,
        rowId: 'id',
        columns: columns,
        fnCreatedRow: function( nRow, aData, iDataIndex ) {
             $(nRow).addClass('status'+aData['status']);
        }
    } );
};


function race_create_form_init(slug) {

    // monthly disabled by default
    $("#id_repeatMonthN").addClass("disabled").attr("disabled", true);
    $("#id_repeatDay").addClass("disabled").attr("disabled", true);
    $("#id_number").addClass("disabled").attr("disabled", true);

    $("#id_repeat").change(function() {
        if ($(this).val() == 'none') {
            $("#id_number").addClass("disabled").attr("disabled", true);
        } else {
            $("#id_number").removeClass("disabled").attr("disabled", false);
        }
        if ($(this).val() == 'monthly') {
            $("#id_repeatMonthN").removeClass("disabled").attr("disabled", false);
            $("#id_repeatDay").removeClass("disabled").attr("disabled", false);
        } else {
            $("#id_repeatMonthN").addClass("disabled").attr("disabled", true);
            $("#id_repeatDay").addClass("disabled").attr("disabled", true);
        }
    });

    $("#submitracecreateform").click(function(){
        $.ajax({
            type: "POST",
            url: slug,
            data: $('#racecreateform').serialize(),
            success: function(msg){
                if (msg['success']) {
                   $("#raceCreateModal").modal('hide');
                   /* force a page refresh to race list page */
                   window.location = slug;
               } else {
                    for (field in msg) {
                        $("#id_"+field).parent().addClass("has-error");
                        $("#id_"+field).parent().children(".help-block").text(msg[field]);
                    }
                }
            }
        });
    });
};

function edit_race_modal_init() {
    $('#raceEditModal').on('show.bs.modal', function(event) {

        var button = $(event.relatedTarget); // Button that triggered the modal
        var raceurl = button.data('raceurl');
        var racename = button.data('racename');
        var raceid = button.data('raceid');
        var clubslug = button.data('clubslug');
        var modal = $(this);

        modal.find('.modal-title').text('Edit Race' );

        $.ajax({
            url: raceurl
        }).done(function(data) {
            form = modal.find('form')[0];

            // fill in form values from this race
            $('input[id=id_date]').val(data.date);
            $('input[id=id_starttime]').val(data.starttime);
            $('input[id=id_signontime]').val(data.signontime);
            $('input[id=id_title]').val(data.title);
            $('input[id=id_website]').val(data.website);
            $('select[id=id_location]').val(data.location.id);
            $('select[id=id_status]').val(data.status);
            $('input[id=id_website]').val(data.website);
            $('textarea[id=id_description]').val(data.description);

            $('select[id=id_category]').val(data.category.key);
            $('select[id=id_licencereq]').val(data.licencereq.key);
            $('select[id=id_discipline]').val(data.discipline.key);

        });

        $("#submitraceeditform").off("click");
        $("#submitraceeditform").click(function(){
            $.ajax({
                type: "POST",
                url: "/races/" + raceid + "/update/",
                data: $('#raceeditform').serialize(),
                success: function(msg){
//                    if (msg['success']) {
                       $("#raceEditModal").modal('hide');
                       populate_race_table(clubslug, true);
//                   } else {
//                        for (field in msg) {
//                            $("#id_"+field).parent().addClass("has-error");
//                            $("#id_"+field).parent().children(".help-block").text(msg[field]);
//                        }
//                    }
                }
            });
        });
    });
};

function add_people_init() {

    $('#addPeopleModal').on('show.bs.modal', function (event) {
      var button = $(event.relatedTarget); // Button that triggered the modal
      var raceurl = button.data('raceurl');
      var racename = button.data('racename');
      var raceid = button.data('raceid');
      var modal = $(this);

      // get the race details via ajax
      $.ajax({
          url: raceurl
      }).done(function(data) {
          // set the default values in the form
          modal.find('.modal-title').text('Add People for Race on ' + data.date );
          form = modal.find('form')[0];
          form.action = '/races/' + raceid + '/officials/';
          $(form).find("input[name='raceid']").val(data.id);

          if (data.officials.Commissaire) {
              $('select[name=commissaire]').val(data.officials.Commissaire[0].id);
          } else {
              $('select[name=commissaire]').val('NONE');
          }
          if (data.officials['Duty Officer']) {
              $('select[name=dutyofficer]').val(data.officials['Duty Officer'][0].id);
          } else {
              $('select[name=dutyofficer]').val('NONE');
          }

          if (data.officials['Duty Helper']) {
              // need a list of ids for the multiple select widget
              var helpers = [];
              for (var i=0; i<data.officials['Duty Helper'].length; i++) {
                  helpers.push(data.officials['Duty Helper'][i].id);
              }
              $('select[name=dutyhelper]').val(helpers);
          } else {
              $('select[name=dutyhelper]').val("");
          }
          // refresh the bootstrap select widget
          $('.selectpicker').selectpicker('refresh');

          // attach the submit handler, replace any existing
          $(form).off('submit');
          $(form).submit(submit_add_people);

      })
  });
}

function submit_add_people(event) {
    event.preventDefault();
    var $form = $( this ),
        commissaire = $form.find( "select[name='commissaire']" ).val(),
        dutyofficer = $form.find( "select[name='dutyofficer']" ).val(),
        dutyhelpers = $form.find( "select[name='dutyhelper']" ).val(),
        raceid = $form.find( "input[name='raceid']").val(),
        url = $form.attr( "action" );

    // get form values, special value 'NONE' gives us the empty list
    var comms = [{id: commissaire}];
    if (commissaire == "NONE") { comms = []; }
    var dos = [{id: dutyofficer}];
    if (dutyofficer == "NONE") { dos = []; }
    var dhs = [];
    if (dutyhelpers) {
        for (var i=0; i<dutyhelpers.length; i++) {
            dhs.push({id: dutyhelpers[i]});
        }
    }
    var officials = {
        'Commissaire': comms,
        'Duty Officer': dos,
        'Duty Helper': dhs
    }

    // post request to add the person to the race
    $.ajax({
        type: "POST",
        url: url,
        data: JSON.stringify(officials),
        contentType: 'application/json',
        processData: false,
        success: function(msg) {
                    // update the page...
                    raceinfo = $('#racetable').DataTable().row('#'+raceid).data();
                    raceinfo.officials = msg;
                    $('#racetable').DataTable().row('#'+raceid).data( raceinfo );
                    $('#addPeopleModal').modal('hide');
                 }
    });
}

function delete_race_init() {
    $('#raceDeleteModal').on('show.bs.modal', function (event) {
      var button = $(event.relatedTarget); // Button that triggered the modal
      var raceurl = button.data('raceurl'); // Extract info from data-* attributes
      var racename = button.data('racename');

      var modal = $(this);
      modal.find('.modal-title').text('Delete Race ' + racename );
      modal.find('form')[0].action = raceurl;
      modal.find('#race_delete_name').innerHTML = racename;

      $("#submitdeleteform").click(function(){

          var racedeleteurl = $("#racedeleteform").attr('action');

          $.ajax({
              type: "DELETE",
              url: racedeleteurl,
              data: $('#racedeleteform').serialize(),
              success: function(msg){
                     $("#raceDeleteModal").modal('hide');
                     /* force a page refresh */
                     window.location = window.location;
              },
              error: function(req, status, msg){
                  $("#raceDeleteModal").modal('hide');
                  alert("You don't have permission to delete this race.");
              }
          });
      });
  });

}


$('#editResultModal').on('show.bs.modal', function (event) {
  var button = $(event.relatedTarget);
  var rider = button.data('rider');
  var place = button.data('place');
  var number = button.data('number');
  var resultid = button.data('resultid');
  var usual_grade = button.data('usual_grade');

  var resulturl = '/api/raceresults/' + resultid + '/';

  var modal = $(this);
  var theform = modal.find('form')[0];

    console.log("usual grade", usual_grade);

  modal.find('.modal-title').text('Edit Result for ' + rider);
  modal.find('#id_place').val(place);
  modal.find('#id_number').val(number);
  modal.find('#id_usual_grade').val(usual_grade);

  theform.action = resulturl;

  $(theform).submit(submit_result_update_form);
});

function submit_result_update_form(event) {
    event.preventDefault();

    var theform = $( this ),
        resulturl = theform.attr( "action" );

    $.ajax({
        type: "PATCH",
        url: resulturl,
        data: theform.serialize(),
        success: function(msg){
               $("#editResultModal").modal('hide');
               /* force a page refresh */
               window.location = window.location;
        },
        error: function(req, status, msg){
            $("#editResultModal").modal('hide');
            alert("You don't have permission to update this result.");
        }
    });
}
