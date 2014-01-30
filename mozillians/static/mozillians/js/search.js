$(function(){

	// Open up to show advanced options
	$('#advanced').click(function(){
		$('.search-options').slideToggle('fast');
	});

	//Autofocus search box when 's' is pressed
	var search_focus_key = 83;// 's'
	var searchInput = $('#homepage-search > input:nth-child(1)');
	$(document).keydown(function( event ){
		if(event.which == search_focus_key && searchInput.is(':focus') == false){
			searchInput.focus();
			event.preventDefault();//to prevent from writing 's' in input		
		}
	}); 
});
