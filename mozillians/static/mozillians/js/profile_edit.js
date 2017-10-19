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
    var uri = URI(location.href);
    var next_section = uri.query(true).next;
    var content = uri.hash();
    if (next_section) {
      content = '#' + next_section;
    }
    if (content) {
        $('ul.nav a[href="' + content + '"]').tab('show');
    }
    if (screen.width < mobile_breakdown) {
        $('.settings-nav > li').removeClass('active');
        $('#profile').show();
        $('#mylocation').show();
        $('#mylocation').addClass('in');
    }
    $('.settings-all').on('click', function() {
        $(this).hide();
        $('.tab-pane').show();
        $('.tab-pane').addClass('in');
    });

    // Privacy toggle buttons
    $('.privacy-toggle').on('click', function(e) {
        e.preventDefault();
        var firstchoice = $(this);
        // This is an array with multiple objects
        var otherChoices = $(this).siblings().not('input');
        var target = $(this).closest('.btn-group').find('input');
        firstchoice.addClass('active');
        $.each(otherChoices, function(index) {
            $(this).removeClass('active');
        });
        var choice = (firstchoice.hasClass('active') ? firstchoice : otherChoices.filter('.active'));
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

    // Show tooltip on hover on desktops and on click on touch devices.
    // Disable tooltip on recaptcha iframe
    $(document).not('.g-recaptcha iframe').tooltip();
    $('#skills').on('DOMNodeInserted', 'li', function() {
        $('.select2-selection__choice').each(function(index, elem){
            $(this).attr('title', '');
        });
    });

    // Django autcomplete light - django cities light
    $(':input[name$=country]').on('change', function() {
        // reset city and region on country change
        $(':input[name=city]').val(null).trigger('change');
        $(':input[name=region]').val(null).trigger('change');
    });

    $(':input[name$=region]').on('change', function() {
        // reset city on region change
        $(':input[name=city]').val(null).trigger('change');
    });

    // Intercept all the ajax calls
    $(document).ajaxSend(function(event, xhr, settings) {
        // Hijack the ajax calls and set the X-CSRFToken Header for
        // the skills-autocomplete/ url.
        // This is needed because we don't have a csrf cookie due to
        // django-session-csrf
        if (settings.url.indexOf('/skills-autocomplete/') != -1) {
            // remove form errors if any
            $('#skill-ajax-error').remove();

            if (settings.type === 'POST') {
                var csrf_token = $('input[name="csrfmiddlewaretoken"]')[0].value;
                xhr.setRequestHeader('X-CSRFToken', csrf_token);
            }
        }
    });

    // Handle ajax errors
    $(document).ajaxError(function(event, xhr, settings, thrownError) {
        if ((settings.url.indexOf('/skills-autocomplete/') != -1) &&
            (settings.type === 'POST')) {
            // remove the user selection that failed the validation
            $('li.select2-results__option').remove();
            $('li.select2-search').children().val = '';

            // Display an error message
            var error_element = ('<span id="skill-ajax-error" class="error-message"> ' +
                                 xhr.responseJSON['message'] +
                                 '</span>');
            $('#skills').find('.form-group').after(error_element);
        }
    });

});
