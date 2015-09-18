$(function() {
    'use strict';

    var mobile_breakdown = 992;
    var default_privacy_value = 3;

    // Favicon
    var url = $("link[rel='shortcut icon']").remove().attr('href');
    var favicon = document.createElement('link');
    favicon.type = 'image/x-icon';
    favicon.rel = 'shortcut icon';
    favicon.href = url;
    $('head').append(favicon);

    // Tabs
    $('.settings-tab').hide();
    var uri = URI(location.href);
    var next_section = uri.query(true).next;
    var hash = uri.hash();
    if (next_section) {
      content = '#' + next_section;
    } else {
      content = hash;
    }
    if (content) {
        $(content + '-tab').show();
        $(content + '-li').addClass('active');
    } else {
        $('#profile-tab').show();
        $('.settings-nav').children('li').first().addClass('active');
        location.hash = '#profile';
    }
    $('.settings-nav > li > a').on('click', function(e) {
        e.preventDefault();
        $('.settings-tab').hide();
        $('.settings-nav > li').removeClass('active');
        $(this).parent('li').addClass('active');
        var content = $(this).attr('href');
        $(content + '-tab').show();
        location.hash = content;
    });
    if (screen.width < mobile_breakdown) {
        $('.settings-tab').show();
        $('.settings-nav > li').removeClass('active');
    }
    $('.settings-all').on('click', function() {
        $(this).hide();
        $('.settings-tab').removeClass('hidden-sm');
        $('.settings-tab').removeClass('hidden-xs');
    });

    // Privacy toggle buttons
    $('.privacy-toggle').on('click', function(e) {
        e.preventDefault();
        var firstchoice = $(this);
        var secondchoice = $(this).siblings().not('input');
        var target = $(this).closest('.btn-group').find('input');
        firstchoice.addClass('active');
        secondchoice.removeClass('active');
        var choice = (firstchoice.hasClass('active') ? firstchoice : secondchoice);
        target.val(choice.data('value'));
    });

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
    var $del = $('#delete-profile');
    $del.click(function(e) {
        if (! $ack.is(':checked')) {
            e.preventDefault();
        }
    });
    $ack.click(function(e) {
        if ($ack.is(':checked')) {
            $del.removeClass('disabled');
        }
        else {
            $del.addClass('disabled');
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
        var $parElement = $(selector).parent();
        var $totalElement = $parElement.find('#id_' + type + '-TOTAL_FORMS');
        var total = $totalElement.val();
        $newElement.find(':input').not(':button').each(function() {
            var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
            var id = 'id_' + name;
            $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
        });
        $newElement.find('label').each(function() {
            var newFor = $(this).attr('for').replace('-' + (total-1) + '-','-' + total + '-');
            $(this).attr('for', newFor);
        });
        total++;
        $totalElement.val(total);
        $newElement.find('.errorlist').remove();
        $newElement.removeClass('error');
        $(selector).after($newElement);
        $newElement.find('.privacy-controls').find('input:hidden').val(default_privacy_value);
    }

    $('#accounts-addfield').click(function() {
        cloneFormsetField('div#accounts > div:last', 'externalaccount_set');
        return false;
    });

    $('#languages-addfield').click(function() {
        cloneFormsetField('div#languages > div:last', 'language_set');
        return false;
    });

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

    // Show tooltip on hover on desktops and on click on touch devices.
    $(document).tooltip();
});
