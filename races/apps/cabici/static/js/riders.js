/*
    Provide services around riders
 */


/*
    riderSelect - turn a form text input into a rider
    select input with autocompletion of rider names
    `formfields` arg is an object describing other form
    fields that should be populated from the rider data
    key is a jQuery selector for the field, value is a function
    that takes the rider data and returns the value to be
    inserted into that field
    eg:
       $('#rider').riderSelect({
        '#rider-id': function (d) {
            return d.id
        },
        '[name=grade]': function (d) {
            return d.grades['WaratahMastersCC']
        },
        '[name=licenceno]': function (d) {
            return d.licenceno
        }
    })
 */
$.fn.riderSelect = function(formfields) {

    var rider_api_url = "/api/riders/?prefix=%QUERY"
    var self = this

    var riderComplete = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('last_nam'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: rider_api_url,
            wildcard: '%QUERY',
            filter: function(resp) {
                return resp.results
            }
        }
    });

    riderComplete.initialize()

    $(self).typeahead({
        name: 'riders',
        displayText: function (datum) {
            return datum.first_name + " " + datum.last_name + " (" + datum.club + ")"
        },
        items: 'all',
        sorter: function(items) {
            return items.sort(function(a, b) {
                var nameA = a.last_name + a.first_name
                var nameB = b.last_name + b.first_name
                if (nameA < nameB) {
                    return -1;
                }
                if (nameA > nameB) {
                    return 1;
                }
                return 0;
            })
        },
        source: riderComplete.ttAdapter(),
        afterSelect: function (data) {
            for (var key in formfields) {
                $(key).val(formfields[key](data))
            }
        }
    }).click(function(event) {
        // reset the input when we click on it again
        var $input = $(self);
        //add something to ensure the menu will be shown
        $input.val('*');
        $input.typeahead('lookup');
        $input.val('');
    })
    return self
}

