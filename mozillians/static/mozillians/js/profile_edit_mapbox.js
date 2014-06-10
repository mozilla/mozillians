'use strict';
(function(){
    // DOM ELEMENTS
    var display_country = $('#display_country');
    var display_region = $('#display_province');
    var display_city = $('#display_city');
    var save_region = $('#id_saveregion');
    var save_city = $('#id_savecity');

    var set_latitude = $('#id_lat');
    var set_longitude = $('#id_lng');

    var search_el = $('#location_search');
    var results_el = $('#location_search_results');
    var loading_el = $('#location .loading');


    // MAPBOX
    var mapboxString = $('div#map').data('mapboxid');
    var map, you, bounds_country, bounds_region, bounds_city;

    var display_bounds = false;

    var style_country = {
        color: 'rgb(255, 198, 166)',
        weight:4,
        opacity:1,
        fillOpacity:0
    };

    var style_region = {
        color: 'rgb(121, 243, 111)',
        weight:4,
        opacity:1,
        fillOpacity:0.05
    };

    var style_city = {
        color: 'rgb(44, 213, 255)',
        weight:4,
        opacity:1,
        fillOpacity:0.1
    };

    var style_hidden = {
        fillOpacity: 0,
        opacity:0
    };


    // GEOCODERS
    function forwardGeocode(query){
        loading_el.show();
        $.ajax({
            url:'https://api.tiles.mapbox.com/v3/'+mapboxString+'/geocode/'+query+'.json',
            success:function(data){
                results_el.children().remove();
                loading_el.hide();
                for (var i = 0; i < data.results.length; i++) {
                    var result = data.results[i];
                    var text = '';
                    for (var j = 0; j < result.length; j++) {
                        text += result[j].name;
                        if(j < result.length-1) text += ', ';
                    }
                    var item = $('<li>').text(text).appendTo(results_el);
                    item[0].datum = result;
                }
                if(data.results.length > 0){
                    results_el.show();
                }else{
                    results_el.hide();
                }
            }
        });
    }

    function reverseGeocode(coordinates, init){
        $.ajax({
            url:'https://api.tiles.mapbox.com/v3/'+mapboxString+'/geocode/'+coordinates.lng+','+coordinates.lat+'.json',
            success: function(data){
                you.setLatLng(data.results[0][0]);
                displayResults(data.results[0]);
                var youLatLng = you.getLatLng();
                set_latitude.val(youLatLng.lat);
                set_longitude.val(youLatLng.lng);
                if (init) {
                    var region_name = display_region.data('mapbox');
                    var city_name = display_city.data('mapbox');
                    if (!region_name) {
                        display_region.text('');
                        save_region.prop('checked', false);
                    }
                    if (!city_name) {
                        display_city.text('');
                        save_city.prop('checked', false);
                    }
                }
            }
        });
    }

    function jumptoGeocode(query){
        $.ajax({
            url:'https://api.tiles.mapbox.com/v3/'+mapboxString+'/geocode/'+query+'.json',
            success: function(data){
                you.setLatLng(data.results[0][0]);
                displayResults(data.results[0]);
                var youLatLng = you.getLatLng();
                set_latitude.val(youLatLng.lat);
                set_longitude.val(youLatLng.lng);
            }
        });
    }

    function displayResults(results){
        display_country.text('');
        display_region.text('');
        display_city.text('');
        bounds_country.setStyle(style_hidden);
        bounds_region.setStyle(style_hidden);
        bounds_city.setStyle(style_hidden);
        save_region.prop('checked', false);
        save_city.prop('checked', false);

        if(results !== undefined){
            var zoomed = false;
            for(var i=0; i<results.length; i++){
                var bounds_converted = undefined;
                if(results[i].bounds !== undefined){
                    bounds_converted = [
                        [results[i].bounds[1],results[i].bounds[0]],
                        [results[i].bounds[3],results[i].bounds[2]]
                    ];
                }
                if(results[i].type === 'city'){
                    display_city.text(results[i].name);
                    save_city.prop('checked', true);
                    if(bounds_converted !== undefined){
                        if(!zoomed){
                            map.fitBounds(bounds_converted);
                            zoomed = true;
                        }
                        if(display_bounds){
                            bounds_city.setBounds(bounds_converted);
                            bounds_city.setStyle(style_city);
                        }
                    }
                }
                if(results[i].type === 'province'){
                    display_region.text(results[i].name);
                    save_region.prop('checked', true);
                    if(bounds_converted !== undefined){
                        if(!zoomed){
                            map.fitBounds(bounds_converted);
                            zoomed = true;
                        }
                        if(display_bounds){
                            bounds_region.setBounds(bounds_converted);
                            bounds_region.setStyle(style_region);
                        }
                    }
                }
                if(results[i].type === 'country'){
                    display_country.text(results[i].name);
                    if(bounds_converted !== undefined){
                        if(!zoomed){
                            map.fitBounds(bounds_converted);
                            zoomed = true;
                        }
                        if(display_bounds){
                            bounds_country.setBounds(bounds_converted);
                            bounds_country.setStyle(style_country);
                        }
                    }
                }
            }
        }
    }


    // SEARCH
    function selectSearchResult(listItem){
        displayResults(listItem.datum);
        map.setView(listItem.datum[0]);

        you.setLatLng([listItem.datum[0].lat,listItem.datum[0].lon]);

        set_latitude.val(listItem.datum[0].lat);
        set_longitude.val(listItem.datum[0].lon);

        results_el.hide();
    }


    // MAP
    map = L.map('map')
        .setView([0, 0], 3)
        .addLayer(L.mapbox.tileLayer(mapboxString, {
            detectRetina: true,
            minZoom: 1,
        }));
    map.scrollWheelZoom.disable();

    map.attributionControl.addAttribution('© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors');

    you = L.marker([0,0],{
        draggable:true
    }).addTo(map);

    you.on('dragend',function(event){
        reverseGeocode(event.target.getLatLng());
    });

    bounds_country = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);
    bounds_region = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);
    bounds_city = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);


    // INIT FOR EXISTING FORM DATA
    var country_name = display_country.data('mapbox');
    var region_name = display_region.data('mapbox');

    var latlng = [
        set_latitude.val(),
        set_longitude.val()
    ];
    if(!isNaN(parseFloat(latlng[0])) && !isNaN(parseFloat(latlng[1]))){
        reverseGeocode({
            lat: latlng[0],
            lng: latlng[1]
        }, true);

    }
    else {
        // No lat/lng, try to center the map based on country & region names if available.
        if (region_name) {
            display_region.text(region_name);
            jumptoGeocode(region_name);
        }
        else if (country_name) {
            display_region.text(country_name);
            jumptoGeocode(country_name);
        }
    }



    // INIT PAGE ELEMENTS
    results_el.hide();
    loading_el.hide();


    // EVENTS
    var keystrokeTimer = undefined;

    $('#location_search_button').click(function(){
        forwardGeocode(search_el.val());
        results_el.show();
    });

    results_el.on('click', 'li', function(){
        selectSearchResult(this);
    });

    search_el.on('keydown changed', function(event){
        if(event.keyCode === 13){ // enter
            event.preventDefault();
            selectSearchResult(results_el.children('li')[0]);
            results_el.hide();
        }else{ // all other keys
            clearTimeout(keystrokeTimer);
            keystrokeTimer = setTimeout(function(){
                if(search_el.val() !== ''){
                    forwardGeocode(search_el.val());
                }else{
                    loading_el.hide();
                    results_el.hide();
                }
            },200);
        }
    });
}());
