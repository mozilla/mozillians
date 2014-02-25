$(function(){
    $id_accepting_new_members = $('#id_accepting_new_members');
    // Hide/show new member criteria field based on moderation
    function checkCriteria(modVal) {
        if(modVal === 'by_request') {
            $('#id_new_member_criteria_fieldset').show();
        } else {
            $('#id_new_member_criteria_fieldset').hide();
        }
    }

    // Hide/show field when moderation field changes
    $id_accepting_new_members.change(function() {
        checkCriteria($(this).val());
    });

    // Hide/show field when document loads
    checkCriteria($id_accepting_new_members.val());
});
