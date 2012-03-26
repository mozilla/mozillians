var app = {
    Profiles: null
}; // Let's namespace our app's functions in here.

(function($) {
    $().ready(function() {
        $('html').removeClass('no-js').addClass('js');

        // Return the current locale (found in the body attribute
        // as a data attribute).
        app.locale = $('body').data('locale');

        // Return a localized URL.
        app.localeUrl = function(url) {
            return '/' + app.locale + '/' + url.toString();
        };

        // Apply language change once another language is selected
        $('#language').change(function() {
            $('#language-switcher').submit();
        });
    });
})(jQuery);
