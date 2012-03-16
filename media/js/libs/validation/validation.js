// All validation functionality for forms
// Current Assumptions: All validated fields are required fields.
var Validator = function() {
    var displayError = function(field, message) {
        var control_group = field.parents('.control-group')
        var error_message = $('<span class="help-inline"></span>');

        // wipe out any existing error messages for this field so
        // we don't have duplicates

        control_group.addClass('error')
        control_group.children('span.help-inline').remove()
        control_group.find('p.help-block').before(error_message.text(message))


        this.errors = true;
    }

    var self = {
        validateEmail: function(email) {
            var email_pattern = /^([\w-\.\+]+@([\w-]+\.)+[a-zA-Z]{2,})?$/;

            if (!email_pattern.test(email.val())) {
                displayError(email, gettext('Enter a valid e-mail address.'));
            } else if ($.trim(email.val()).length < 1) {
                displayError(email, gettext('This field is required.'));
            } else {
                this.resetField(email.attr('name') + '-container');
            }
        },
        validatePassword: function(password) {
            var limit = 8;

            if ($.trim(password.val()).length < 8) {
                displayError(password, gettext('Ensure this value has at least 8 characters.'));
            } else {
                var field = '#' + password.attr('name') + '-container';
                this.resetField(field);
            }
        },
        validateLastName: function(last_name) {
            if ($.trim(last_name.val()).length < 1) {
                displayError(last_name, gettext('This field is required.'));
            } else {
                var field = '#' + last_name.attr('name') + '-container';
                this.resetField(field);
            }
        },
        validateGroup: function(group, field) {
            var name = group.children('span').text();
            if (name.match(/^[a-zA-Z0-9 .:,-]*$/g) === null) {
                displayError(field, gettext('Groups can only contain ' +
                                            'alphanumeric characters, dashes, ' +
                                            'spaces.'));
                // HACK: Do this without dirty DOM manipulation.
                group.children('a.tagit-close').click();
            }
        },
        resetField: function(field) {
            $(field).removeClass('error');
            $(field + ' .errorlist').remove();
            $(field).find('span.required').show();
            this.errors = false;
        }
    };

    return self;
};

$(function() {
    app.validator = Validator();
    app.validator.errors = false;
    var form = $('form');

    form.delegate('#id_email, #id_password, #id_last_name', 'focus', function() {
        var field = '#' + $(this).attr('name') + '-container';
        app.validator.resetField(field);
    });

    form.delegate('#id_email', 'blur', function() {
        var email = $(this);
        app.validator.validateEmail(email);
    });

    form.delegate('#id_password', 'blur', function() {
        var password = $(this);
        app.validator.validatePassword(password);
    });

    form.delegate('#id_last_name', 'blur', function() {
        var last_name = $(this);
        app.validator.validateLastName(last_name);
    });
});
