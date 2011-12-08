(function($) {
    $().ready(function() {
        var bid_login_a = '<a href="#">' + $('#browserid-login span').text() + '</a>';
        $('#browserid-login span').replaceWith(bid_login_a);

        var bid_reg_a = '<a class="browserid-register" href="#">' + $('#browserid-register span').text() + '</a>';
        $('#browserid-register span').replaceWith(bid_reg_a);

        $('#browserid-login a, #browserid-retry-login').click(_bid_fn('login'));
        $('.browserid-register').click(_bid_fn('register'));
    });
    /**
     * Sets up BrowserID callback.
     * mode - login or register
     *
     * Fragile magick - forms are named browserid-login 
     * and browserid-register
     */
    var _bid_fn = function(mode) {
        return function(event) {
            var form;
            event.preventDefault();
            navigator.id.getVerifiedEmail(function(assertion) {
                if (assertion) {
                    form = $('form#browserid');
                    $('#id_assertion', form).attr('value', assertion.toString());
                    $('#bid_mode', form).attr('value', mode);
                    form.submit();
                }
            });
        };
    };
})(jQuery);
