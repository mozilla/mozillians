/*
 * Api specific javascript
 */

$(function(){

    var queryParameters = {}, queryString = location.search.substring(1), re = /([^&=]+)=([^&]*)/g, m;
    while (m = re.exec(queryString)) {
        queryParameters[decodeURIComponent(m[1])] = decodeURIComponent(m[2]);
    };
    queryParameters['format'] = 'json';
    $.ajax({
        url: window.location.pathname,
        data: queryParameters
    }).done(function(msg) {
        $("#json").html(JSON.stringify(msg, undefined, 2));
        $("#json_url").attr("href", this.url).html(this.url);
        prettyPrint();
    });
})
