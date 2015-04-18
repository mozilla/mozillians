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

    // Reset unused externalaccount fields to default privacy.
    $('#form-submit').on('click', function(event) {
        event.preventDefault();
        $('.externalaccount-fieldrow').each(function(index, obj) {
            if ($(obj).children('[id$=username]').val() === '') {
                privacy_field = $(obj).find('[id$=privacy]');
                privacy_field.val(privacy_field.data('privacy-original'));
            }
        });
        $('#edit-profile-form').submit();
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
        $newElement.find('.errorlist').remove();
        $newElement.removeClass('error');
        $(selector).after($newElement);
    }

    $('#accounts .addField').click(function() {
        cloneFormsetField('fieldset#accounts > div > div:last', 'externalaccount_set');
        return false;
    });

    $('#languages .addField').click(function() {
        'use strict';
        cloneFormsetField('fieldset#languages > div:last', 'language_set');
        return false;
    });

    // Show tooltip on hover on desktops and on click on touch
    // devices.


    $('.tshirt-info').on({
        "touchstart mouseenter":function(event) {
            event.preventDefault();
            $(this).addClass('active');
        },
        "touchend mouseleave":function(event) {
            event.preventDefault();
            $(this).removeClass('active');
        },
    });

    $('#id_skills').tagit({
        allowSpaces: true,
        caseSensitive: false,
        singleField: true,
        singleFieldDelimiter: ',',
        removeConfirmation: true,
        tagSource: $('#skills').data('autocomplete-url'),
        triggerKeys: ['enter', 'comma', 'tab']
    });
});
