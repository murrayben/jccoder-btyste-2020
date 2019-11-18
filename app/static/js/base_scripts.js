$(document).on('scroll', function () {
    if ($(window).scrollTop() > 100) {
        $("#scroll-top").fadeIn(500);
    } else {
        $("#scroll-top").fadeOut(500);
    }
});
$(function () {
    $('#scroll-top').hide();
    $('#scroll-top').on('click', function () {
        $("html, body").animate({
            scrollTop: 0
        }, 1000);
    });
    $('[data-toggle="popover"]').popover({
        container: 'body'
    });

    $(window).on('resize', adjustFooter);
    adjustFooter();

    function adjustFooter() {
        if ($(document).width() <= 992) {
            $('footer').css('height', 'auto');
            $('footer').css('marginTop', -1 * $('footer').outerHeight());
            $('#content').css('padding-bottom', $('footer').outerHeight());
        }
    }   
})