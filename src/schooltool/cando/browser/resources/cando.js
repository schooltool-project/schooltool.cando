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
});
