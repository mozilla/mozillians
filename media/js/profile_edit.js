$(function() {
    // Switching all options for profile privacy on select
    $('.privacy-all select').change(function(){
        value = $(this).val();
        if (value === '-1') {
            $('.privacy-choice').each(function() {
                $(this).val($(this).data('privacy-original'));
            });
        }
        else {
            $('.privacy-choice').val(value);
        }
    });

    // Adding and removing fields from create/edit profile form
    $('#websites .addField').click(function() {
        $('<div class="newField"><input type="text" value="" placeholder="" /></label> <a href="#" class="removeField"> <i class="icon-minus-sign"></i> Remove</a></div>').appendTo('#websites');
        return false;
    });

    $('#accounts .addField').click(function() {
        $('<div class="newField"><input type="text" value="" placeholder="" /> <select id="account-choices"><option value="bugzilla">Bugzilla</option><option value="mdn">MDN</option><option value="amo">AMO</option><option value="sumo">SUMO</option><option value="github" selected>Github</option><option value="facebook">Facebook</option><option value="twitter">Twitter</option><option value="aim">AIM</option><option value="yahoo">Yahoo!</option><option value="google">Google Talk</option><option value="skype">Skype</option></select> <a href="#" class="removeField"> <i class="icon-minus-sign"></i> Remove</a></div>').appendTo('#accounts');
        return false;
    });

    $(document).on('click', '.removeField', function() {
        $(this).parents('.newField').remove();
        return false;
    });
});
