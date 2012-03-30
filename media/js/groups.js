(function($) {
    $().ready(function() {
        $('a[href=' + location.hash + ']').tab('show');
        if ($('#body-edit-profile').length) {
            $('#id_groups').tagit({
                allowSpaces: true,
                caseSensitive: false,
                onTagAdded: function(event, group) {
                    app.validator.resetField('#groups-container');
                    app.validator.validateGroup(group, $('#id_groups'));
                },
                singleField: true,
                singleFieldDelimiter: ',',
                removeConfirmation: true,
                tagSource: app.localeUrl('groups/search'),
                triggerKeys: ['enter', 'comma', 'tab']
            });
            $('#id_skills').tagit({
                allowSpaces: true,
                caseSensitive: false,
                onTagAdded: function(event, group) {
                    app.validator.resetField('#groups-container');
                    app.validator.validateGroup(group, $('#id_skills'));
                },
                singleField: true,
                singleFieldDelimiter: ',',
                removeConfirmation: true,
                tagSource: app.localeUrl('skills/search'),
                triggerKeys: ['enter', 'comma', 'tab']
            });
        }
    });
})(jQuery);
