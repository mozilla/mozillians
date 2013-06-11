(function($){
    $().ready(function() {
        if ($('#body-register').length) {
            $('#page1button').bind('click', function() {
                document.getElementById('1').click();
            });
            $('#page2button').bind('click', function() {
                document.getElementById('2').click();
            });
            $('#page3button').bind('click', function() {
                document.getElementById('3').click();
            });
        }


        //messenger service management
        var messengers = [],
            mess_hidden = $('input[name="names"]');
        $('#IM_add')[0].onclick = function() {
            var mess_data={
              'username':$('#id_name').val(),
              'service':$('#id_service').val()
            }
            messengers.push(mess_data);
            messenger_bar();
            mess_hidden.val(JSON.stringify(messengers));
        }

        var messenger_bar = function() {
            var messenger_table = '<table id="messenger_table">';
            $.each(messengers, function(i, m) {
                messenger_table += '<tr>';
                messenger_table += '<td>' + m.service + ' :  </td>';
                messenger_table += '<td>' + m.username +'</td>';
                messenger_table += '<td><a id="mess_remove" name="' + i + '">remove</a>';
                messenger_table += '</tr>';
            })

            messenger_table += '</table>';
            $('#messenger-names').html(messenger_table);
            $('#messenger-data').html()
            $(function(){
                $('#messenger_table').find('#mess_remove').click(function() {
                    mess_removes($(this)[0].name);
                });
                //remove add button when 10 names are added
                if (messengers.length >= 10) {
                    $('#IM_add').css('visibility', 'hidden');
                } else {
                    $('#IM_add').css('visibility', 'visible');
                }
             });
        }

        var mess_removes = function(i) {
            messengers.splice(i,1);
            messenger_bar();
        }
    });
})(jQuery);
