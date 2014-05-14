$('textarea[maxlength]').each(function(){
	this.maxlength = $(this).attr('maxlength');
	this.countdownElement = $(this).parent().find('.character-countdown');
	$(this.countdownElement).text(this.maxlength - this.value.length);
});

$('textarea[maxlength]').on({
    'keydown keyup propertychange input paste':function(){
        $(this.countdownElement).text(this.maxlength - this.value.length);
    }
});
