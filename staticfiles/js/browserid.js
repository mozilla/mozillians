(function($) {
    $().ready(function() {
		$('.browser_id_login').bind('click', function(e) {
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