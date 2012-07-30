ST.cando = function () {
    return {
        column_select_all: function (input) {
            var checkbox = $(input),
                index = checkbox.parent().index(),
                table = checkbox.closest('table'),
                column = table.find('tbody tr').find('td:eq('+index+')'),
                checkboxes = column.find('input[type="checkbox"]');
            checkboxes.attr('checked', checkbox.is(':checked'));
        }
    };
}();

function isScorable(td) {
    return true;
}

function cellInputName(td) {
    return td.attr('id');
}

$(document).ready(function() {
    var container = $('#skill-title');
    var skill_title = container.find('p');
    $('#grades-part').on('mouseover', '.popup_link', function() {
        var link = $(this);
        var th = link.parent();
        skill_title.text(link.attr('title'));
        if (th.hasClass('optional')) {
            skill_title.attr('class', 'optional');
        } else {
            skill_title.attr('class', 'required');
        }
    });
    var normal_width = 748;
    var wide_width = 940;
    $('#gradebook-controls').on('click', '.expand', function() {
        container.css({
            left: 16
        });
        skill_title.css({
            width: wide_width
        });
    });
    $('#gradebook-controls').on('click', '.collapse', function() {
        container.css({
            left: 208
        });
        skill_title.css({
            width: normal_width
        });
    });
    // tertiary navigation
    var third_nav_container = $('#third-nav-container');
    var third_nav = third_nav_container.find('.third-nav');
    var active_tab = third_nav.find('.active');
    var tab_width = active_tab.outerWidth();
    if (third_nav.children().length > 0) {
        var scrollTo = tab_width * (active_tab.index());
        third_nav_container.scrollTo(scrollTo, 0, {axis: 'x'});
        $('#navbar-list-worksheets').removeClass('navbar-arrow-inactive');
    }
    third_nav.on('click', 'li', function(e) {
        if ($('#worksheets-list').length < 1) {
            var ul = createWorksheetsList();
            $('#navbar-list-worksheets').after(ul);
        }
        $('#worksheets-list').slideToggle('fast');
        $('#navbar-list-worksheets').toggleClass('navbar-list-worksheets-active');
        e.preventDefault();
    });
    // student gradebook
    grades = $('#grade-student');
    grades.on('click', 'tbody td.student-score', function() {
        var td = $(this);
        if (isScorable(td)) {
            var input = getInput(td);
            input[0].select();
            input.focus();
        }
    });
    grades.on('click', 'input', function() {
        this.select();
    });
    grades.on('blur', 'input', function() {
        var td = $(this).parent();
        if ($(this).val() === td.attr('original')) {
            removeInput(td);
        }
    });
    grades.on('keyup', 'input', function() {
        var input = $(this);
        var td = input.parent();
        var tr = td.parent();
        if (input.val() !== td.attr('original')) {
            if (this.timer) {
                clearTimeout(this.timer);
            }
            var data = {
                'activity_id': cellInputName(td).split('.')[1],
                'score': input.val()
            };
            var url = tr.attr('class') + '/validate_score';
            this.timer = setTimeout(function () {
                $.ajax({
                    url: url,
                    data: data,
                    dataType: 'json',
                    type: 'get',
                    success: function(data) {
                        input.removeClass();
                        var css_class = 'valid';
                        if (!data.is_valid) {
                            css_class = 'error';
                        } else if (data.is_extracredit) {
                            css_class = 'extracredit';
                        }
                        input.addClass(css_class);
                    }
                });
            }, 200);
        }
    });
    grades.on('keydown', 'input', function(e) {
        var td = $(this).parent();
        var tr = td.parent();
        switch(e.keyCode) {
        case 27: // escape
            $(this).val(td.attr('original'));
            $(this).blur();
            e.preventDefault();
            break;
        case 38: // up
            focusInputVertically(tr.prevUntil('tbody'), td.index());
            e.preventDefault();
            break;
        case 13: // enter
        case 40: // down
            focusInputVertically(tr.nextAll(), td.index());
            e.preventDefault();
            break;
        }
    });
});
