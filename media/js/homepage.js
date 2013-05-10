// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

$(function() {
  /* Mosaic image rotations
  ================================================== */
  $('#mosaic-top, #mosaic-bottom' ).gridrotator( {
      rows    : 3,
      columns   : 15,
      animType  : 'fadeInOut',
      animSpeed : 1000,
      interval  : 2000,
      step    : 1,
      w480    : {
        rows  : 2,
        columns : 7
      },
      w320    : {
        rows  : 2,
        columns : 5
      }
  });

  /* Back to top button
  ================================================== */
  var a = $('#back-to-top');

  $(a).hide().removeAttr("href");

  $(window).scroll(function() {
    $(this).scrollTop() >= 200 ? $(a).fadeIn("slow") : $(a).fadeOut("slow");
  });

  $(a).click(function(){
    $('html, body').animate({ scrollTop: "0px"}, 1200);
  });


});