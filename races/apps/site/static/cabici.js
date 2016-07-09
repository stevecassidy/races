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
      var raceurl = button.data('raceurl'); // Extract info from data-* attributes
      var racename = button.data('racename');
      var raceid = button.data('raceid');

      // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
      // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
      var modal = $(this);
      modal.find('.modal-title').text('Add People for Race on ' + racename );
      form = modal.find('form')[0];
      form.action = raceurl;
      $(form).find("input[name='raceid']").val(raceid);
      $(form).submit(submit_add_people);
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

    var prefix = $(location).attr('protocol') + "//" + $(location).attr('host');
    var jj= {
        'role': "Duty Officer",
        'rider': prefix + '/api/riders/' + dutyofficer + '/',
        'race': prefix + '/api/races/' + raceid + '/'
    }
    console.log(jj);
    // post request to add the person to the race
    $.post('/api/racestaff/', jj);

    jj['role'] = "Commissaire";
    jj['rider'] = prefix + '/api/riders/' + commissaire + '/',
    $.post('/api/racestaff/', jj)
    console.log(jj);

    $.each(dutyhelpers, function(idx, dh) {
        jj['role'] = "Duty Helper";
        jj['rider'] = prefix + '/api/riders/' + dh + '/',
        $.post('/api/racestaff/', jj);
        console.log(jj);
    });

    $('#addPeopleModal').modal('hide');

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
