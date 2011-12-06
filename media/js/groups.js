(function($) {
    $().ready(function() {
        if ($('#body-edit-profile').length) {
            $('#id_groups').tagit({
                allowSpaces: true,
                caseSensitive: false,
                onTagAdded: function(event, tag) {
                    var name = tag.children('span').text();
                    if (name.match(/^[a-zA-Z0-9 .:,-]*$/g) === null) {
                        // HACK: Do this without dirty DOM manipulation.
                        $(tag).children('a.tagit-close').click();
                    }
                },
                singleField: true,
                singleFieldDelimiter: ',',
                removeConfirmation: true,
                tagSource: app.localeUrl('groups-search'),
                triggerKeys: ['enter', 'comma', 'tab']
            });
        }
    });
})(jQuery);
