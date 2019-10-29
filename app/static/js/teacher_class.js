$(function () {
    // Preventing collapse from opening/closing when checkboxes are clicked
    $('.content-toggler .assignment-checkbox').on('click', function(e) {
        e.stopPropagation();
    });

    // Collapse arrows
    $('.content div').on('click', function() {
        var $arrow = $(this).children('.d-flex').children('.arrow');
        if ($arrow.children('.fa-chevron-right').length > 0) {
            $arrow.html('<i class="fas fa-chevron-down fa-fw" aria-hidden="true"></i>')
        } else {
            $arrow.html('<i class="fas fa-chevron-right fa-fw" aria-hidden="true"></i>')
        }
    });

    // View more content dropdown
    $('.module-dropdown').on('click', function(e) {
        e.preventDefault();
        $('.module-dropdown.active').removeClass('active');
        $(this).addClass('active');
        showContent();
    });
    showContent();

    function showContent() {
        $('.content[data-parent-type="module"]').hide();
        $('.content-collapse').collapse('hide');
        var $content = $('.content[data-parent-type="module"][data-parent-id="' + $('.module-dropdown.active').data('module') + '"]');
        $content.show();
        $($content.data('target') + '.content').show(); // Because of nested collapses
        $('.arrow').html('<i class="fas fa-chevron-right fa-fw" aria-hidden="true"></i>'); // Reset arrows
    }

    // Checkbox tick all functionality
    $('.assignment-checkbox input').on('change', function() {
        var $this = $(this);
        if (!$this.hasClass('page-checkbox') && !$this.hasClass('quiz-checkbox')) {
            $('.content[data-parent-type="' + $this.data('type') + '"][data-parent-id="' + $this.data('id') + '"]').children('.content-toggler').children('.d-flex').children('.assignment-checkbox').children('input').prop('checked', this.checked).change();
        }
        if ($this.data('type') !== 'chapter') {
            var $parent = $this.parent().parent().parent().parent();
            var $inputs = $('.content[data-parent-type="' + $parent.attr('data-parent-type') + '"][data-parent-id="' + $parent.attr('data-parent-id') + '"] .assignment-checkbox input')
            var count_checked = 0;
            $inputs.each(function() {
                if (this.checked) {
                    count_checked++;
                }
            });
            if (this.checked && (count_checked === $inputs.length)) {
                $('.assignment-checkbox input[data-type="' + $parent.attr('data-parent-type') + '"][data-id="' + $parent.attr('data-parent-id') + '"]').prop('checked', true);
            } else if (!this.checked && (count_checked !== $inputs.length)) {
                $('.assignment-checkbox input[data-type="' + $parent.attr('data-parent-type') + '"][data-id="' + $parent.attr('data-parent-id') + '"]').prop('checked', false);
            }
        }

        var count = $('.assignment-checkbox input:checked.page-checkbox, .assignment-checkbox input:checked.quiz-checkbox').length;
        if (count === 0) {
            count = "";
        }
        var $assign_btn = $('#assign-btn');
        $('.no-assigned-items').text(count);
        if (!count) {
            $assign_btn.prop('disabled', true);
        } else {
            $assign_btn.prop('disabled', false);
        }
    });
    $('#assign-btn').prop('disabled', true);

    $('#due_date').attr('autocomplete', 'off').datepicker({dateFormat: 'dd-mm-yy', minDate: '+1D'});
    $('#submit').hide();
    

    if (window.location.href.indexOf('assignments_page=') > -1) {
        setTimeout(function() {$('#assignments-tab').click();}, 50);
    }

    

    function reindexIDs() {
        i = 0;
        $('[name="new-username"]').each(function() {
            i++;
            this.id = 'new-username' + i;
        });
    }

    $('#add-new-username-line').on('click', function() {
        var $cloned_line = $('.username-field').first().clone();
        var $field = $cloned_line.children().first().children().children();
        $field.val('');
        $cloned_line.children('.generated-username').empty();
        $('.username-field').last().after($cloned_line);
        reindexIDs();
        $('.delete-username a').css('visibility', 'visible');
        $('.delete-username a').first().css('visibility', 'hidden');
        $field.focus();
    });

    $('#username-table-body').on('click', '.delete-username-btn', function() {
        $(this).parent().parent().remove();
        reindexIDs();
    });
    
    $('#username-table-body').on('keydown', '[name="new-username"]', function() {
        if (event.keyCode == 13) {
            $('#add-new-username-line').click();
        }
    });

    $('.page-hyperlink, .quiz-hyperlink').on('click', function(e) {
        e.preventDefault();
        var $this = $(this);
        var is_page = $this.hasClass('page-hyperlink');
        
        $('#pageModal').modal('show');
        if (is_page) {
            // Page
            loadPageContent($this, $this.data('pageId'), is_quiz=false, preview=true)

        } else {
            loadPageContent($this, $this.data('quizId'), is_quiz=true, preview=true)
        }
    });

    $('.delete-student').on('click', function(e) {
        e.preventDefault();
        if (confirm('Are you sure you want to remove this student from the class?')) {
            window.location.href = this.href;
        }
    });
});