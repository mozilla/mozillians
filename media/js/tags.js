(function($) {
    $().ready(function() {
        if ($('#body-edit-profile').length) {
            $('#id_tags').tagit({
                caseSensitive: false,
                singleField: true,
                singleFieldDelimiter: ' ',
                removeConfirmation: true,
                tagSource: app.localeUrl('tags/search')
                // triggerKeys: ['enter', 'comma', 'tab']
            });
        }
    });
})(jQuery);
