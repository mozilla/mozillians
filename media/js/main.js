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

        // Footer hovers when window width is greater than 480px
        var getWinWidth = $(window).width();
        if(getWinWidth > 480){
          var $footer = $("footer");
          var default_h = $footer.height();
          var rollover_h = $footer.find(".rollover").height();
          $footer.css({"bottom":-rollover_h, position:"fixed"});
          $("#main.container").css("padding-bottom", default_h);
          $(window).resize(function(){
            rollover_h = $footer.find(".rollover").height();
            $footer.css({"bottom":-rollover_h});
          });
          $footer.hover(function() {
            $(this).stop().animate({bottom:"0"}, 500);
          }, function() {
            $(this).stop().animate({"bottom":-rollover_h}, 500);
          });
        }
    });
})(jQuery);
