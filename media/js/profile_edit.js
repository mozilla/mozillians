
$(document).ready(function() {
    // Switching all options for profile privacy on select
    $('.privacy-all select').change(function(){
        value = $(this).val();
        if (value === '-1') {
            $('.privacy-choice').each(function() {
                $(this).val($(this).data('privacy-original'));
            });
        }
        else {
            $('.privacy-choice').val(value);
        }
    });

    // Messenger service management 
    var csrftoken = $('[name="csrfmiddlewaretoken"]')[0].value,
        purl = $('#IM_add').val(),
        messenger_remove_url = $('#messenger_delete').text();

    var messenger_bar = function(data) {
        var messenger_table = '<table id="messenger_table">';
        $.each(JSON.parse(data), function(i, mess) {
            messenger_table += '<tr>';
            messenger_table += '<td>' + mess.fields.service + ' :  </td>';
            messenger_table += '<td>' + mess.fields.name + '</td>';
            messenger_table += '<td><a id="mess_remove" name="' + mess.pk + '">remove</a>';
            messenger_table += '</tr>';

        });
        messenger_table += '</table>';
        $('#messenger-names').html(messenger_table); 
        $(function(){
            //click event for the remove button
            $('#messenger_table').find('#mess_remove').click(function() {
                if ( confirm('Delete?') ) {
                  mess_removes($(this)[0].name);
                }
            });
            //hide add button when 10 names are added
            messengers = $('#messenger_table').find('#mess_remove').length
            if (messengers >= 10) {
              $('#IM_add').css('visibility', 'hidden');
            } else {
              $('#IM_add').css('visibility', 'visible');
            }
         });
     }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    });

    // The POST, refreshes #messenger-names on success
    $('#IM_add')[0].onclick = function() {
        var postdata={
          'username':$('#id_name').val(),
          'service':$('#id_service').val()
        }
        pstring = JSON.stringify(postdata);
        
        $.ajax({
             type:"POST",
             url:purl,
             dataType: "json",
             data: pstring,
             success: function(data) {
                messenger_bar(data);
            }
        });
    }

    var mess_removes = function(name) {
        var postdata={
          'messenger_pk':name
        }
        pstring = JSON.stringify(postdata);
        $.ajax({
             type:"POST",
             url:messenger_remove_url,
             dataType: "json",
             data: pstring,
             success: function(data) {
                messenger_bar(data);
            }
        });
    }
    
    var get_list = function() {
        $.ajax({
             type:"GET",
             url:purl,
             success: function(data) {
                messenger_bar(data);
            }
        });

    }
    get_list();

});
