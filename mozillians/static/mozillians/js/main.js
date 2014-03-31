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

        // Collapses nav menu when user has clicked outside the dropdown
        function collapseNavMenu () {
            $('.dropdown-menu').hide();
            $('i.icon-reorder').removeClass('open');
            $('#outer-wrapper').off('click', collapseNavMenu);
        }

        // Main nav dropdown
        $('a.dropdown-toggle').on('click', function(e) {
            var $icon = $('i.icon-reorder');
            e.stopPropagation();

            $('.dropdown-menu').toggle();
            $icon.toggleClass('open');

            // If the nav is open listen for clicks outside the dropdown
            if ($icon.hasClass('open')) {
                $('#outer-wrapper').on('click', collapseNavMenu);
            } else {
                $('#outer-wrapper').off('click', collapseNavMenu);
            }
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

        // Focus search when 's' key is pressed
        $('body').keypress(function(event){
            if (event.which==115 && !$('input, textarea, select').is(':focus')) {
                $searchbox = $('.search-query, #search-form input[type=text]');
                $searchbox.focus();
                event.preventDefault();
            }
        });
    });

    // april fools 2014 - 3d mode
    $('#three-dee-toggle').click(function(event) {
        event.preventDefault();
        $('body').toggleClass('three-dee');
        var q = $('body').hasClass('three-dee');
        $(this).children('img').attr('src','/static/mozillians/img/3d-'+q+'.png');
    });
})(jQuery);
