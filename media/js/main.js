(function($) {
    $().ready(function() {
        $('html').removeClass('no-js').addClass('js');

        // Apply language change once another language is selected
        $('#language').change(function() {
            $('#language-switcher').submit();
        });
    });
})(jQuery);
