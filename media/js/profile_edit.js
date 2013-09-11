$(function() {
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

    // Make deleting harder
    var $ack = $('#delete input:checkbox');
    var $del = $('#delete .delete');
    $del.click(function(e) {
        if (! $ack.is(':checked')) {
            e.preventDefault();
        }
    });
    $ack.click(function(e) {
        if ($ack.is(':checked')) {
            $del.css({opacity: 1});
        }
        else {
            $del.css({opacity: 0.2});
        }
    });

    // takes a jquery selector and the type of a formset to duplicate fields
    function cloneFormsetField(selector, type) {
        var $newElement = $(selector).clone(true);
        var total = $('#id_' + type + '-TOTAL_FORMS').val();
        $newElement.find(':input').each(function() {
            var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
            var id = 'id_' + name;
            $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
        });
        $newElement.find('label').each(function() {
            var newFor = $(this).attr('for').replace('-' + (total-1) + '-','-' + total + '-');
            $(this).attr('for', newFor);
        });
        total++;
        $('#id_' + type + '-TOTAL_FORMS').val(total);
        $(selector).after($newElement);
    }

    // Adding and removing fields from create/edit profile form
    $('#websites .addField').click(function() {
        $('<div class="newField"><input type="text" value="" placeholder="" /></label> <a href="#" class="removeField"> <i class="icon-minus-sign"></i> Remove</a></div>').appendTo('#websites');
        return false;
    });

    $('#accounts .addField').click(function() { 
        cloneFormsetField('fieldset#accounts > div:last', 'externalaccount_set')
        return false;
    });

    $('.tshirt-info').click(function() {
        $(this).toggleClass('active');
        return false;
    });

});
