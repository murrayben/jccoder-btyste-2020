$(function() {
    var content = $('#content').val();
    function updateForm() {
        if (Number($('#page_type').val()) === 1) {
            // Article
            $('#content').val(content);
            $('.md-editor').parent().fadeIn();
        }

        if (Number($('#page_type').val()) === 2) {
            // Quiz
            $('#content').val('Quiz');
            $('.md-editor').parent().fadeOut();
        }
    }

    $('#page_type').on('change', updateForm);
    updateForm();
});