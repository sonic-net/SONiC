jQuery(function ($) {
    // Load contributors from the /assets/data/contributors.json file
    $.getJSON('/assets/data/contributors.json', function (data) {
        // Data is an array in format {name: "Name", image: "URL", "url": "URL"}
        var contributors = data.map(function (contributor) {
            return '<li><a href="' + contributor.url + '" title="' + contributor.name + '" target="_blank">' +
                '<img src="' + contributor.image + '" alt="' + contributor.name + '" />' +
                '</a></li>';
        });
        $('#contributors').html(contributors.join(''));
    });
});