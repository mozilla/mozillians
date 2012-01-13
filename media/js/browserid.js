(function($) {
    $().ready(function() {
		$('#create_profile').bind('click', function(e) {
		  e.preventDefault();
		  navigator.id.getVerifiedEmail(function(assertion) {
		    if (assertion) {
		      var $e = $('#id_assertion');
		      $e.val(assertion.toString());
		      $e.parent().submit();
		    }
		  });
		});
    });
})(jQuery);