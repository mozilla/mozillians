$(function(){

	// Hide/show new member criteria field based on moderation
	$( "#id_accepting_new_members" ).change(function() {
	    if($(this).val() == "by_request") {
		$('#id_new_member_criteria_fieldset').show();
	    } else {
		$('#id_new_member_criteria_fieldset').hide();
	    }
	});

});
