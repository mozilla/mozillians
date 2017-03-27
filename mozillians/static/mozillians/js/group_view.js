$(function() {
    'use strict';

    // Show tooltip on hover on desktops and on click on touch devices.
    $(document).tooltip();

    // Keep filter parameter across pagination
    function append_filtr() {
        var filtr = $('#id_filtr option:selected').val();

        // Append filter to pagination option values
        $('#pagination-form select option').each(function(index) {
            var paginator_uri = URI($(this).val());
            paginator_uri.removeSearch('filtr');
            paginator_uri.addSearch('filtr', filtr);
            $(this).val(paginator_uri);
        });

        // Append filter to prev/next buttons
        $('.pagination a').each(function(index) {
            var paginator_uri = URI($(this).attr('href'));
            paginator_uri.removeSearch('filtr');
            paginator_uri.addSearch('filtr', filtr);
            $(this).attr('href', paginator_uri);
        });
    }

    // On filter init/change update paginator
    $('#id_filtr').ready(append_filtr);
    $('#id_filtr').change(append_filtr);
});
