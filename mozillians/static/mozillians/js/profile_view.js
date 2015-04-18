$(document).ready(function() {
    $("#view-privacy-mode").change(function() {
        window.location = this.value;
    });

    /* If we know the offset of the profile's time zone, add a tooltip */
    var $section = $("section#timezone");
    if ($section) {
      var offset = $section.attr("data-timezone-offset");  /* in minutes */
      if (offset !== "notset") {
        /* get the browser's current timezone offset in minutes */
        /* javascript gives it in the opposite direction we're expecting, so negate it */
        var browser_offset = -(new Date()).getTimezoneOffset();
        var diff = (offset - browser_offset) / 60;  /* convert from minutes to hours */
        var msg_template;
        if (diff > 0) {
          msg_template = $("span#hours_ahead_text").text();
        } else if (diff < 0) {
          diff = -diff;
          msg_template = $("span#hours_behind_text").text();
        } else {
          msg_template = $("span#same_timezone_text").text();
        }
        $section.attr("title", msg_template.replace("%HOURS%", diff));
      }
    }
});
