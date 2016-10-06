var _gaq = _gaq || [];
var pluginUrl = '//www.google-analytics.com/plugins/ga/inpage_linkid.js';
var _gaAccountCode = document.documentElement.getAttribute('data-ga-code');

_gaq.push(['_setAccount', _gaAccountCode]);
_gaq.push(['_setAllowLinker', true]);
_gaq.push(['_setAllowAnchor', true]);
_gaq.push(['_gat._anonymizeIp']);
_gaq.push(['_trackPageview']);

if (_gaAccountCode) {
    (function() {
        var ga = document.createElement('script');
        ga.type = 'text/javascript';
        ga.async = true;
        ga.src = '/static/mozillians/js/libs/ga.js';
        ga.integrity = 'sha384-qlg7xB42NGK87oFd2d7ZRqeY0XYyrD4wrKw4VhhH8r13OtxJp2UzLymBSaRfN1gK';
        ga.crossorigin = 'anonymous';

        var s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(ga, s);

        var ga_inpage_linkid = document.createElement('script');
        ga_inpage_linkid.type = 'text/javascript';
        ga_inpage_linkid.async = true;
        ga_inpage_linkid.src = '/static/mozillians/js/libs/inpage_linkid.js';
        ga_inpage_linkid.integrity = 'sha384-sO8ot6WvES5SlygqvT4HdbvgpOsfet1pGROTyNYdMicwjCjOXwU48ITHK8EkNzzp';
        ga_inpage_linkid.crossorigin = 'anonymous';

        s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(ga_inpage_linkid, s);

    })();
}
