/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

(function($, window) {
    'use strict';

    // State? Ewwwwww.
    var loginRedirect = null; // Path to redirect to post-login.
    var logoutRedirect = null; // Path to redirect to post-logout.
    var loginCallback = null; // Callback to run post-login.

    // Public API
    window.django_browserid = {
        /**
         * Triggers BrowserID login.
         * @param {string} next URL to redirect the user to after login.
         * @param {object} requestArgs Options to pass to navigator.id.request.
         */
        login: function login(next, requestArgs) {
            var defaults = $('#browserid-info').data('requestArgs');
            requestArgs = $.extend({}, defaults, requestArgs);

            loginRedirect = next;
            navigator.id.request(requestArgs);
        },

        /**
         * Triggers BrowserID logout.
         * @param {string} next URL to redirect the user to after logout.
         */
        logout: function logout(next) {
            logoutRedirect = next;
            navigator.id.logout();
        },

        /**
         * Check to see if the current user has authenticated via
         * django_browserid.
         * @return {boolean} True if the user has authenticated, false
         *                   otherwise.
         */
        isUserAuthenticated: function isUserAuthenticated() {
            return !!$('#browserid-info').data('userEmail');
        },

        /**
         * Retrieve an assertion from BrowserID and execute a callback.
         * @param {function} Callback to run after requesting an assertion.
         */
        getAssertion: function getAssertion(callback, requestArgs) {
            var defaults = $('#browserid-info').data('requestArgs');
            requestArgs = $.extend({}, defaults, requestArgs);

            loginCallback = callback || null;
            navigator.id.request(requestArgs);
        },

        /**
         * Verify that the given assertion is valid, and redirect to another
         * page if successful.
         * @param {string} Assertion to verify.
         * @param {string} URL to redirect to after successful verification.
         */
        verifyAssertion: function verifyAssertion(assertion, redirectTo) {
            var $loginForm = $('#browserid-form'); // Form used to submit login.
            $loginForm.find('input[name="next"]').val(redirectTo);
            $loginForm.find('input[name="assertion"]').val(assertion);
            $loginForm.submit();
        }
    };

    $(function() {
        var $loginForm = $('#browserid-form'); // Form used to submit login.
        var $browseridInfo = $('#browserid-info'); // Useful info from backend.

        var loginFailed = location.search.indexOf('bid_login_failed=1') !== -1;

        // Call navigator.id.request whenever a login link is clicked.
        $(document).on('click', '.browserid-login', function(e) {
            e.preventDefault();
            django_browserid.login($(this).data('next'));
        });

        // Call navigator.id.logout whenever a logout link is clicked.
        $(document).on('click', '.browserid-logout', function(e) {
            e.preventDefault();
            django_browserid.logout($(this).attr('href'));
        });

        navigator.id.watch({
            loggedInUser: $browseridInfo.data('userEmail') || null,
            onlogin: function(assertion) {
                // Avoid auto-login on failure.
                if (loginFailed) {
                    navigator.id.logout();
                    loginFailed = false;
                    return;
                }

                if (isFunction(loginCallback)) {
                    loginCallback(assertion);
                } else if (assertion) {
                    django_browserid.verifyAssertion(assertion, loginRedirect);
                }
            },
            onlogout: function() {
                // Follow the logout link's href once logout is complete.
                var currentLogoutUrl = logoutRedirect;
                if (currentLogoutUrl !== null) {
                    logoutRedirect = null;
                    window.location = currentLogoutUrl;
                } else {
                    // Sometimes you can get caught in a loop where BrowserID
                    // keeps trying to log you out as soon as watch is called,
                    // and fails since the logout URL hasn't been set yet.
                    // Here we just find the first logout button and use that
                    // URL; if this breaks your site, you'll just need custom
                    // JavaScript instead, sorry. :(
                    currentLogoutUrl = $('.browserid-logout').attr('href');
                    if (currentLogoutUrl) {
                        window.location = currentLogoutUrl;
                    }
                }
            }
        });
    });

    // Courtesy of http://jsperf.com/alternative-isfunction-implementations/9
    function isFunction(obj) {
        return typeof(obj) == 'function';
    }
})(jQuery, window);
