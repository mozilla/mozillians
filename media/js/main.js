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

        //Main nav dropdown
        $('a.dropdown-toggle').click(function() {
            $('.dropdown-menu').toggle();
            $('i.icon-reorder').toggleClass('open');
        });

        /* Back to top button
        ================================================== */
        var a = $('#back-to-top');

        $(a).hide().removeAttr("href");

        $(window).scroll(function() {
          $(this).scrollTop() >= 200 ? $(a).fadeIn("slow") : $(a).fadeOut("slow");
        });

        $(a).click(function(){
          $('html, body').animate({ scrollTop: "0px"}, 1200);
        });

        $('input, textarea').placeholder(); 
    });
})(jQuery);
