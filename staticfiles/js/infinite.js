(function($) {
    'use strict';
    $().ready(function() {
        var paginator = $('.pagination');
        var results = $('#final-result')
        var pages = paginator.attr('data-pages');
        // Variable to keep track of whether we've reached our max page
        var cease;
        paginator.hide();
        results.hide();

        // If there is no paginator, don't do any scrolling
        cease =  (pages == undefined)

        $(document).endlessScroll({
            // Number of pixels from the bottom at which callback is triggered
            bottomPixels: 750,
            // Wait a second before we even think of loading more content
            fireDelay: 1000,
            fireOnce: true,
            ceaseFire: function() {
                return cease;
            },
            callback: function(i) {
                cease = (pages < i);
                if (cease) {
                    // Show the user that we have stopped scrolling on purpose.
                    results.show()
                } else {
                    $.ajax({
                        data:{'page': i + 1},
                        dataType: 'html',
                        success: function(data) {
                            paginator.before($(data));
                        }
                    });
                }

            }
        });
    });
})(jQuery);
