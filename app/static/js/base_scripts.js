
$(function () {
    $(document).on('scroll', toggleScrollTop);
    function toggleScrollTop () {
        if ($(window).scrollTop() > 100) {
            $("#scroll-top").fadeIn(500);
        } else {
            $("#scroll-top").fadeOut(500);
        }
    }
    $('#scroll-top').hide();
    $('#scroll-top').on('click', function () {
        $("html, body").animate({
            scrollTop: 0
        }, 1000);
    });
    $('[data-toggle="popover"]').popover({
        container: 'body'
    });

    $('.modal').on('show.bs.modal', function() {
        $(document).off('scroll', toggleScrollTop);
        $('#scroll-top').hide();
    });

    $('.modal').on('hide.bs.modal', function() {
        $(document).on('scroll', toggleScrollTop);
        toggleScrollTop();
    });

    $(window).on('resize', adjustFooter);
    var $footer = $('footer');
    var $content = $('#content');
    adjustFooter();

    function adjustFooter() {
        if ($(document).width() <= 992) {
            $footer.css('height', 'auto');
            $footer.css('marginTop', -1 * $('footer').outerHeight() + 20);
            $content.css('padding-bottom', $('footer').outerHeight());
        } else {
            $footer.css({
                height: 157,
                marginTop: -157
            });
            $content.css('padding-bottom', 177);
        }
    }   
})