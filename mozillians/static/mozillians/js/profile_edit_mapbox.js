(function(){
    'use strict';


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
    var search_loading_el = $('#location_search_loading');
    var gps_loading_el = $('#location_gps_loading');


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
    var xhr = $.ajax();

    function forwardGeocode(query,takeFirstResult){
        if(query){
            if(takeFirstResult){ results_el.hide(); }
            search_loading_el.show();
            xhr.abort();
            xhr = $.ajax({
                url:'https://api.tiles.mapbox.com/v3/'+mapboxString+'/geocode/'+query+'.json',
                success:function(data){
                    results_el.children().remove();
                    search_loading_el.hide();
                        for (var i = 0; i < data.results.length; i++) {
                            var result = data.results[i];
                            var type = data.results[i][0].type;
                            if(type === 'country' || type === 'province' || type === 'city'){
                                var text = '';
                                for (var j = 0; j < result.length; j++) {
                                    text += result[j].name;
                                    if(j < result.length-1) text += ', ';
                                }
                                var item = $('<li>').text(text).appendTo(results_el);
                                item[0].datum = result;
                            }
                        }
                        if(results_el.children().length !== 0){
                        if(takeFirstResult){
                            selectSearchResult(results_el.children().first()[0].datum);
                        }else{
                            results_el.show();
                        }
                        }else{
                            results_el.hide();
                        }
                    }
            });
        }
    }

    function reverseGeocode(coordinates, modifyForm){
        xhr.abort();
        xhr = $.ajax({
            url:'https://api.tiles.mapbox.com/v3/'+mapboxString+'/geocode/'+coordinates.lng+','+coordinates.lat+'.json',
            success: function(data){
                you.setLatLng(data.results[0][0]);
                displayResults(data.results[0], modifyForm);
                var youLatLng = you.getLatLng();
                if(modifyForm){
                    set_latitude.val(youLatLng.lat);
                    set_longitude.val(youLatLng.lng);
                }
            }
        });
    }


    // DISPLAY
    function displayResults(results, modifyForm){
        display_country.text('');
        display_region.text('');
        display_city.text('');
        bounds_country.setStyle(style_hidden);
        bounds_region.setStyle(style_hidden);
        bounds_city.setStyle(style_hidden);
        if (modifyForm) {
            save_region.prop('checked', false);
            save_city.prop('checked', false);
        }

        if(results !== undefined){
            var zoomed = false;
            var centered = false;
            for(var i=0; i<results.length; i++){
                var bounds_converted;
                if(results[i].bounds !== undefined){
                    bounds_converted = [
                        [results[i].bounds[1],results[i].bounds[0]],
                        [results[i].bounds[3],results[i].bounds[2]]
                    ];
                }
                if(results[i].type === 'city'){
                    display_city.text(results[i].name);
                    if (modifyForm) {
                        save_city.prop('checked', true);
                    }
                    if(bounds_converted !== undefined){
                        if(!zoomed){
                            map.fitBounds(bounds_converted);
                            zoomed = true;
                        }
                        if(!centered){
                            you.setLatLng([results[i].lat,results[i].lon]);
                            centered = true;
                        }
                        if(display_bounds){
                            bounds_city.setBounds(bounds_converted);
                            bounds_city.setStyle(style_city);
                        }
                    }
                }
                if(results[i].type === 'province'){
                    display_region.text(results[i].name);
                    if (modifyForm) {
                        save_region.prop('checked', true);
                    }
                    if(bounds_converted !== undefined){
                        if(!zoomed){
                            map.fitBounds(bounds_converted);
                            zoomed = true;
                        }
                        if(!centered){
                            you.setLatLng([results[i].lat,results[i].lon]);
                            centered = true;
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
                        if(!centered){
                            you.setLatLng([results[i].lat,results[i].lon]);
                            centered = true;
                        }
                        if(display_bounds){
                            bounds_country.setBounds(bounds_converted);
                            bounds_country.setStyle(style_country);
                        }
                    }
                }
            }
            map.panTo(you.getLatLng());
            results_el.hide();
        }
    }


    // SEARCH
    function selectSearchResult(searchResult){
        displayResults(searchResult, true);

        you.setLatLng([searchResult[0].lat,searchResult[0].lon]);

        set_latitude.val(searchResult[0].lat);
        set_longitude.val(searchResult[0].lon);
    }


    // LOCATE ME VIA GPS
    function locateMe(){
        navigator.geolocation.getCurrentPosition(handleLocating, handleError,
        {
            enableHighAccuracy:false, //location will get re-approximated anyway
            maximumAge: 900000 //15 minutes
        });
    }

    function handleLocating(geoposition){
        reverseGeocode({
            lat: geoposition.coords.latitude,
            lng: geoposition.coords.longitude
        },true);
        gps_loading_el.hide();
    }

    function handleError(error){
        gps_loading_el.hide();
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
        reverseGeocode(event.target.getLatLng(),true);
    });

    bounds_country = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);
    bounds_region = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);
    bounds_city = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);


    // INIT FOR EXISTING FORM DATA
    var mapbox_country = display_country.data('mapbox');
    var mapbox_region = display_region.data('mapbox');
    var mapbox_city = display_city.data('mapbox');
    var latlng = {
        lat: set_latitude.val(),
        lng: set_longitude.val()
    };

    if(!isNaN(parseFloat(latlng.lat)) && !isNaN(parseFloat(latlng.lng))){
        // use coordinates if present
        you.setLatLng(latlng);
        reverseGeocode(latlng,false);
        if (!mapbox_region) {
            display_region.text('');
            save_region.prop('checked', false);
        }
        if (!mapbox_city) {
            display_city.text('');
            save_city.prop('checked', false);
        }
    }else{
        // no coordinates. run a search with the text that's available
        // assume profiles with city always comes with lat/lng
        if(mapbox_region){
            display_region.text(mapbox_region);
            forwardGeocode(mapbox_region,true);
        }else if(mapbox_country){
            display_country.text(mapbox_country);
            forwardGeocode(mapbox_country,true);
        }
    }


    // INIT PAGE ELEMENTS
    results_el.hide();
    search_loading_el.hide();
    gps_loading_el.hide();


    // EVENTS
    var keystrokeTimer;

    $('#location_search_button').click(function(){
        forwardGeocode(search_el.val());
    });

    $('#location_gps_button').click(function(){
        results_el.hide();
        gps_loading_el.show();
        locateMe();
    });

    results_el.on('click', 'li', function(){
        selectSearchResult(this.datum);
    });

    search_el.on('keydown changed', function(event){
        clearTimeout(keystrokeTimer);
        if(event.keyCode === 13){ // enter
            event.preventDefault();
            forwardGeocode(search_el.val(),true);
        }else{ // all other keys
            keystrokeTimer = setTimeout(function(){
                if(search_el.val() !== ''){
                    forwardGeocode(search_el.val(),false);
                }else{
                    search_loading_el.hide();
                    results_el.hide();
                }
            },250);
        }
    });
}());
