function destroyExtras() {
    $('.css-extra, .js-extra').remove();
}

function loadPageContent(pageEl, page_id, is_quiz=false, preview=false) {
    // Send ajax request to server to retrieve page content
    data = {id: page_id, is_quiz: is_quiz, is_preview: preview}
    $.ajax({
        url: '/page-content/',
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: 'application/json; charset=utf-8',
        type: 'POST',
        success: function(response) {
            var pageTitle = response.page_title;
            var pageHTML = response.page_html;
            var css = response.css;
            var js = response.js;

            $('#pageModal').on('hidden.bs.modal', function() {
                destroyExtras();
                $('#pageModal #page-html').empty();
            });
            if (preview) {
                $('#pageModal #page-title').text('Preview: ' + pageTitle);
            } else {
                $('#pageModal #page-title').text(pageTitle);
            }
            $('#pageModal #page-html').html(pageHTML);
            $('#pageModal #page-html img').addClass('img-fluid');
            $('#go-to-page').attr('href', pageEl.attr('href'));
            $('#page-type').text(response.page_type);

            $('.css-extra').detach().appendTo($('head'));
            $('.js-extra').each(function() {
                $(this).detach().appendTo($('body'));
            });

            // Scroll to the top
            $('#page-html').animate({
                scrollTop: 0
            }, 0.00000000000000000001);
            if (!pageEl.data('next-page-id')) {
                $('#next-page').hide().off('click');
            } else {
                $('#next-page').show().on('click', function(e) {
                    e.preventDefault();
                    destroyExtras();
                    var nextPage = pageEl.parent('p').next().children('a');
                    pageLink = nextPage.href;
                    $('#next-page').off('click');
                    loadPageContent(nextPage, pageEl.data('next-page-id'))
                });
            }
        },
        error: function(error) {
            $('#pageModal #page-title').text('Error');
            $('#pageModal #page-html').text('There has been an error in retrieving the content.')
        }
    });
}