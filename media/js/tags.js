(function($) {
    $().ready(function() {
        if ($('#body-edit-profile').length) {
            $('#id_tags').tagit({
                // itemName: 'tags',
                caseSensitive: false,
                singleField: true,
                singleFieldDelimiter: ' ',
                removeConfirmation: true,
                tagSource: '/en-US/tags/search'
                // triggerKeys: ['enter', 'comma', 'tab']
            });
        }
    });
})(jQuery);
