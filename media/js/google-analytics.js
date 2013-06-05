var _gaq = _gaq || [];
var pluginUrl = '//www.google-analytics.com/plugins/ga/inpage_linkid.js';
var _gaAccountCode = document.documentElement.getAttribute('data-ga-code');

_gaq.push(['_require', 'inpage_linkid', pluginUrl]);
_gaq.push(['_setAccount', _gaAccountCode]);
_gaq.push(['_setAllowLinker', true]);
_gaq.push(['_setAllowAnchor', true]);
_gaq.push(['_trackPageview']);

if (_gaAccountCode) {
    (function() {
        var ga = document.createElement('script');
        ga.type = 'text/javascript';
        ga.async = true;

        var prefix = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www');
        ga.src = prefix + '.google-analytics.com/ga.js';


        var s = document.getElementsByTagName('script')[0];
        s.parentNode.insertBefore(ga, s);
    })();
}
