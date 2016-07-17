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

    $("#submitraceform").click(function(){
        $.ajax({
            type: "POST",
            url: slug,
            data: $('#raceform').serialize(),
            success: function(msg){
                if (msg['success']) {
                   $("#raceCreateModal").modal('hide');
                   /* force a page refresh */
                   window.location = window.location;
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

function add_people_init() {
    $('#addPeopleModal').on('show.bs.modal', function (event) {
      var button = $(event.relatedTarget); // Button that triggered the modal
      var raceurl = button.data('raceurl');
      var racename = button.data('racename');
      var raceid = button.data('raceid');
      var modal = $(this);

      console.log(raceurl);
      // get the race details via ajax
      $.ajax({
          url: raceurl
      }).done(function(data) {
          console.log(data);
          // set the default values in the form
          modal.find('.modal-title').text('Add People for Race on ' + data.date );
          form = modal.find('form')[0];
          form.action = '/races/' + raceid + '/officials/';
          $(form).find("input[name='raceid']").val(data.id);

          if (data.officials.Commissaire) {
              $('select[name=commissaire]').val(data.officials.Commissaire[0].id);
          }
          if (data.officials['Duty Officer']) {
              $('select[name=dutyofficer]').val(data.officials['Duty Officer'][0].id);
          }

          if (data.officials['Duty Helper']) {
              // need a list of ids for the multiple select widget
              var helpers = [];
              for (var i=0; i<data.officials['Duty Helper'].length; i++) {
                  helpers.push(data.officials['Duty Helper'][i].id);
              }
              $('select[name=dutyhelper]').val(helpers);
          }
          // refresh the bootstrap seleect widget
          $('.selectpicker').selectpicker('refresh');
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

    var comms = [{id: commissaire}];
    var dos = [{id: dutyofficer}];
    var dhs = [];
    for (var i=0; i<dutyhelpers.length; i++) {
        dhs.push({id: dutyhelpers[i]});
    }

    var officials = {
        'Commissaire': comms,
        'Duty Officer': dos,
        'Duty Helper': dhs
    }

    console.log(officials);
    console.log(url);
    // post request to add the person to the race
    $.ajax({
        type: "POST",
        url: url,
        data: JSON.stringify(officials),
        contentType: 'application/json',
        processData: false,
        success: function(msg) {
                    console.log(msg);
                    // update the page...
                    raceinfo = $('#racetable').DataTable().row('#'+raceid).data();
                    console.log(raceinfo);
                    raceinfo.officials = msg;
                    console.log(raceinfo);
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

      // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
      // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
      var modal = $(this);
      modal.find('.modal-title').text('Delete Race ' + racename );
      modal.find('form')[0].action = raceurl;
      modal.find('#race_delete_name').innerHTML = racename;

      $("#submitdeleteform").click(function(){

          var racedeleteurl = $("#racedeleteform").attr('action');
          console.log("Action " + racedeleteurl);

          $.ajax({
              type: "DELETE",
              url: racedeleteurl,
              data: $('#racedeleteform').serialize(),
              success: function(msg){
                     $("#raceDeleteModal").modal('hide');
                     /* force a page refresh */
                     window.location = window.location;
              }
          });
      });
  });

}
