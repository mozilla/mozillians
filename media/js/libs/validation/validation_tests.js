$(function() {
    var email_field = $('#id_email');
    var password_field = $('#id_password');
    var last_name_field = $('#id_last_name');

    app.validator = Validator();

    test("email should be valid",
    function() {
        var email1 = 'test@test.org';
        var email2 = 'test+test@test.org';
        var email3 = 's@l.info';

        app.validator.validateEmail(email_field.val(email1).blur());
        ok(true, email_field.siblings('.errorlist').length < 1);
        app.validator.validateEmail(email_field.val(email2).blur());
        ok(true, email_field.siblings('.errorlist').length < 1);
        app.validator.validateEmail(email_field.val(email3).blur());
        ok(true, email_field.siblings('.errorlist').length < 1);
    });

    test("email should be invalid",
    function() {
        var email1 = '!@test.org';
        var email2 = 'test+test@.org';
        var email3 = 's@l.';
        var email4 = 'test@test.123'

        app.validator.validateEmail(email_field.val(email1).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
        app.validator.validateEmail(email_field.val(email2).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
        app.validator.validateEmail(email_field.val(email3).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
        app.validator.validateEmail(email_field.val(email4).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
    });

    test("password should be greater than 7 characters",
    function() {
        var password1 = '1';
        var password2 = '12345678';

        app.validator.validatePassword(password_field.val(password1).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
        app.validator.validatePassword(password_field.val(password2).blur());
        ok(true, email_field.siblings('.errorlist').length < 1);
    });

    test("field should not be blank",
    function() {
        var password = '';
        var last_name = '';
        var email = '';

        app.validator.validatePassword(password_field.val(password).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
        app.validator.validatePassword(email_field.val(email).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
        app.validator.validatePassword(last_name_field.val(last_name).blur());
        ok(true, email_field.siblings('.errorlist').length > 0);
    });
});
