new SimpleMDE({element: $('#text')[0], forceSync: true, hideIcons: ["guide"]});
new SimpleMDE({element: $('#solution')[0], forceSync: true, hideIcons: ["guide"]});
$('form').get(0).reset();
var counter = 1;
$('<div class="btn-group" id="btns" />').insertBefore($('#submit'));

var $newOptionBtn = $('<a role="button" class="btn btn-success" id="add-new-option" href="#">Add new option</a>');

var $deleteOptionBtn = $('<a role="button" class="btn btn-danger" id="delete-last-option" href="#">Delete the last option</a>');
$deleteOptionBtn.css('display', 'none');

$('#submit').appendTo('#btns');

updateFields($('#type'));
$('#type').on('change', function () {
    updateFields($(this));
});

$newOptionBtn.click();

function updateMaxAttempts() {
    isSingleAnswer = Number($('#type').val()) === 3 ? true : false;
    if (isSingleAnswer) {
        $('#max_attempts').attr('max', 10);
    } else {
        $('#max_attempts').attr('max', $('[name="options1"]').length - 1);
    }
}

function updateFields(field) {
    var $this = field;
    if (Number($this.val()) === 1) {
        // Multiple Choice
        $('[name="options1"]').parent().fadeIn(1000);
        $('[name="options1"]').val("");
        $deleteOptionBtn.prependTo($('#btns')).hide();
        $deleteOptionBtn.on('click', deleteInput);
        if ($('[name="options1"]').length > 2) {
            $deleteOptionBtn.fadeIn(1000)
        }
        $newOptionBtn.prependTo($('#btns')).hide().fadeIn(1000);
        $newOptionBtn.on('click', addInput);
        $('#answer').prev().text('Answer (first option is 1, second option is 2, etc.)');
        $('#answer').attr('type', 'number');
        $('#answer').attr('min', 1);
        updateMaxAttempts();
    } else if (Number($this.val()) === 2) {
        // Drag and drop
        $('[name="options1"]').parent().fadeIn(1000);
        $('[name="options1"]').val("");
        $deleteOptionBtn.prependTo($('#btns')).hide();
        $deleteOptionBtn.on('click', deleteInput);
        if ($('[name="options1"]').length > 2) {
            $deleteOptionBtn.fadeIn(1000)
        }
        $newOptionBtn.prependTo($('#btns')).hide().fadeIn(1000);
        $newOptionBtn.on('click', addInput);
        $('#answer').prev().text('Answer (in format: table_box_row=option_num)');
        $('#answer').attr('type', 'input');
    } else if (Number($this.val()) === 3) {
        // Single Answer (input type='text')
        $('[name="options1"]').parent().fadeOut(1000, function() {
            $('[name="options1"]').val("Placeholder");
        });
        $newOptionBtn.fadeOut(1000, function() {
            $(this).remove();
        });
        $deleteOptionBtn.fadeOut(1000, function() {
            $(this).remove();
        });
        $('#answer').prev().text('Answer');
        $('#answer').attr('type', 'input');
        updateMaxAttempts();
    }
}

function addInput(e) {
    e.preventDefault();
    var newdiv = $('[name="options1"]').last().clone();
    newdiv.val('');
    newdiv.attr('id', 'options' + counter);
    $(newdiv).insertAfter($('[name="options1"]').last());
    updateMaxAttempts();
    if ($('[name="options1"]').length > 2) {
        $deleteOptionBtn.fadeIn(1000);
    }
    counter++;
}
function deleteInput(e) {
    e.preventDefault();
    if ($('[name="options1"]').length > 2) {
        $('[name="options1"]').last().fadeOut(1000).remove();
        counter--;
    }
    if ($('[name="options1"]').length <= 2) {
        $deleteOptionBtn.fadeOut(1000);
    }
    updateMaxAttempts();
}