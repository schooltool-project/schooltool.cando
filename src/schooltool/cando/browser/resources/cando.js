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
});
