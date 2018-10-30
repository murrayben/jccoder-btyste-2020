$('#scroll-top').hide();
$('#scroll-top').on('click', function () {
    $("html, body").animate({
        scrollTop: 0
    }, 1000);
});
$(document).on('scroll', function () {
    if ($(window).scrollTop() > 100) {
        $("#scroll-top").fadeIn(500);
    } else {
        $("#scroll-top").fadeOut(500);
    }
});