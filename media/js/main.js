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

        // Switching all options for profile privacy on select 
        $('.privacy-all select').change(function(){
            if ($(this).val() != '') {
              $('.privacy-choice').val($(this).val());
            }
        });

        // Shows or hides all fields, based on their value in comparison to dropdown value
        $('#view-privacy-mode').on('change', function () {
            if (($(this).val()) == 'all') {
                $('.privacy-options').show();
            } else {
                $('.privacy-options').hide();
                $('.privacy-options.p-' + $(this).val()).show();
            }
        });
    });
})(jQuery);
