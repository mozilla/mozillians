$(function(){
    $id_accepting_new_members = $('#id_accepting_new_members');
    $id_new_member_criteria_fieldset = $('#id_new_member_criteria_fieldset');
    $id_invalidation_days = $('#id_invalidation_days');
    $id_membership_can_expire = $('#id_membership_can_expire :input');
    $id_group_terms = $('#id_group_terms');
    $id_group_has_terms = $('#id_group_has_terms :input');


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

    // Hide/show field when moderation field changes
    $id_accepting_new_members.change(function() {
        checkCriteria($id_accepting_new_members.val());
    });
    $id_membership_can_expire.change(function() {
        checkMembershipInvalidation();
    });
    $id_group_has_terms.change(function() {
        checkGroupTerms();
    });


    // Hide/show field when document loads
    checkCriteria($id_accepting_new_members.val());
    checkMembershipInvalidation();
    checkGroupTerms();

    $('#curators').on('DOMNodeInserted', 'li', function() {
        $('.select2-selection__choice').each(function(index, elem){
            $(this).attr('title', '');
        });
    });
});
