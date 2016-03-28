$(function() {

    function checksize() {
        if ($("#groups-nav").css("display") == "none" ){
            $('.tab-pane').show();
            $('.tab-pane').removeClass('fade');
        }
    }

    $group_type_choice = $('#grouptype-form input[type="radio"]');
    $accepting_new_members = $('input[name=accepting_new_members]:checked');
    $id_new_member_criteria_fieldset = $('#id_new_member_criteria_fieldset');
    $id_invalidation_days = $('#id_group_invalidation_days');
    $id_membership_can_expire = $('#id_membership_can_expire :input');
    $id_group_terms = $('#id_group_terms');
    $id_group_has_terms = $('#id_group_has_terms :input');
    $id_group_has_email_text = $('#id_group_has_email_text :input');
    $id_group_email_text = $('#id_group_email_text');

    // Hide/show new member criteria field based on moderation
    function checkCriteria(modVal) {
        if(modVal === 'by_request') {
            $id_new_member_criteria_fieldset.show();
        } else {
            $id_new_member_criteria_fieldset.hide();
        }
    }

    function checkMembershipInvalidation() {
        if($id_membership_can_expire.is(':checked')) {
            $id_invalidation_days.show();
        } else {
            $id_invalidation_days.hide();
            $id_invalidation_days.find(':input').val('');
        }
    }

    function checkGroupTerms() {
        if($id_group_has_terms.is(':checked')) {
            $id_group_terms.show();
        } else {
            $id_group_terms.hide();
            $id_group_terms.find(':input').val('');
        }
    }

    function checkGroupEmailText() {
        if($id_group_has_email_text.is(':checked')) {
            $id_group_email_text.show();
        } else {
            $id_group_email_text.hide();
            $id_group_email_text.find(':input').val('');
        }
    }

    // Hide/show field when moderation field changes
    $group_type_choice.on('change', function() {
        $accepting_new_members = $($accepting_new_members.selector);
        checkCriteria($accepting_new_members.val());
    });
    $id_membership_can_expire.change(function() {
        checkMembershipInvalidation();
    });
    $id_group_has_terms.change(function() {
        checkGroupTerms();
    });
    $id_group_has_email_text.change(function() {
        checkGroupEmailText();
    });

    // Initialize membership expiration checkbox
    if ($id_invalidation_days.find(':input').val()) {
        $id_membership_can_expire.prop('checked', true);
    }

    // Initialize terms expiration checkbox
    if ($id_group_terms.find('textarea').val()) {
        $id_group_has_terms.prop('checked', true);
    }
    // Initialize email text checkbox
    if ($id_group_email_text.find('textarea').val()) {
        $id_group_has_email_text.prop('checked', true);
    }


    // Hide/show field when document loads
    checkCriteria($accepting_new_members.val());
    checkMembershipInvalidation();
    checkGroupTerms();
    checkGroupEmailText();

    $('#curators').on('DOMNodeInserted', 'li', function() {
        $('.select2-selection__choice').each(function(index, elem) {
            $(this).attr('title', '');
        });
    });

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
    var content = window.location.hash;
    if (next_section) {
      content = '#' + next_section;
    }
    if (content) {
        $('ul.nav a[href="' + content + '"]').tab('show');
    }

    // Show all settings on mobile
    checksize();
    $(window).resize(checksize);

    // Make deleting harder
    var $ack = $('#delete input:checkbox');
    var $del = $('#delete-group');
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
});
