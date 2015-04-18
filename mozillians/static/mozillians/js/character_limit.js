var textarea = $('textarea[maxlength]');

textarea.each(function(){
	this.maxlength = $(this).attr('maxlength');
	this.countdownElement = $('.character-countdown');
	this.countdownElement.text(this.maxlength - this.value.length);
});

textarea.on({
    'keydown keyup propertychange input paste':function(){
        this.countdownElement.text(this.maxlength - this.value.length);
    }
});
