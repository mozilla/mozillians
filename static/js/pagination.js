$(function(){

	// Pagination dropdown that updates url + directs to
	// corresponding page.
	$('select.page-list').change(function(){
		var url = $(this).val();
		window.location = url;
	});

});
