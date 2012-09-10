(function($){
    $().ready(function() {
        if ($('#body-register').length) {
            $('#page1button').bind('click', function() {
                document.getElementById('1').click();
            });
            $('#page2button').bind('click', function() {
                document.getElementById('2').click();
            });
            $('#page3button').bind('click', function() {
                document.getElementById('3').click();
            });
        }
    });
})(jQuery);
