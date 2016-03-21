$(function() {
    'use strict';

    var $create_group_modal = $('#GroupModal');
    var $create_group_form_errors = $('#GroupModal .add-group .error-message');

    if ($create_group_form_errors.length){
        $create_group_modal.modal('show');
    }
});
