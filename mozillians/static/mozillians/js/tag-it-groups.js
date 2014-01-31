(function($) {
    $().ready(function() {
        if ($('#edit-profile').length || $('#register').length) {
            $('#id_skills').tagit({
                allowSpaces: true,
                caseSensitive: false,
                onTagAdded: function(event, skill) {
                    app.validator.resetField('#groups-container');
                    app.validator.validateSkill(skill, $('#id_skills'));
                },
                singleField: true,
                singleFieldDelimiter: ',',
                removeConfirmation: true,
                tagSource: app.localeUrl('skills/search/'),
                triggerKeys: ['enter', 'comma', 'tab']
            });
            $('#id_languages').tagit({
                allowSpaces: true,
                caseSensitive: false,
                onTagAdded: function(event, group) {
                    app.validator.resetField('#groups-container');
                    app.validator.validateGroup(group, $('#id_languages'));
                },
                singleField: true,
                singleFieldDelimiter: ',',
                removeConfirmation: true,
                tagSource: app.localeUrl('languages/search/'),
                triggerKeys: ['enter', 'comma', 'tab']
            });
        }
    });
})(jQuery);
