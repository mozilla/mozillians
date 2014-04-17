(function($) {
    $().ready(function() {
        if ($('#edit-profile').length || $('#register').length) {
            $('#id_skills').tagit({
                allowSpaces: true,
                caseSensitive: false,
                singleField: true,
                singleFieldDelimiter: ',',
                removeConfirmation: true,
                tagSource: app.localeUrl('skills/search/'),
                triggerKeys: ['enter', 'comma', 'tab']
            });
        }
    });
})(jQuery);
