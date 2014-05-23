var mapboxString = $('div#map').data('mapboxid');

// DOM elements
var display_country = $('#display_country');
var display_region = $('#display_province');
var display_city = $('#display_city');

var display_latitude = $('#id_lat');
var display_longitude = $('#id_lng');

var locate_el = $('#locate');

var map, you, bounds_country, bounds_region, bounds_city;

var style_country = {
	color: "green",
	weight:4,
	opacity:1,
	fillOpacity:0
};

var style_region = {
	color: "yellow",
	weight:4,
	opacity:1,
	fillOpacity:0.1
};

var style_city = {
	color: "red",
	weight:4,
	opacity:1,
	fillOpacity:0.2
};

var style_hidden = {
	fillOpacity: 0,
	opacity:0
}

var marker_added = false;

function reverseGeocode(coordinates){
	var url = 'https://api.tiles.mapbox.com/v3/'
	+mapboxString
	+'/geocode/'
	+coordinates.lng
	+','
	+coordinates.lat
	+'.json';

	$.ajax({
		url: url
	})
	.success(function(data){
//		console.log ('reverse data', data);
		displayResults(data.results[0]);
	});
}

function handleError(err){
//	console.error(err);
}

function handleLocating(geoposition){
//	console.log(geoposition);
	reverseGeocode({
		lat: geoposition.coords.latitude
		,lng: geoposition.coords.longitude
	});
}

function locateMe(){
//	console.log('locating me');
	navigator.geolocation.getCurrentPosition(handleLocating, handleError, { enableHighAccuracy:true });
}

function displayResults(results){
//	console.log('displayResults',results);

	display_country.text('');
	display_region.text('');
	display_city.text('');
	bounds_country.setStyle(style_hidden);
	bounds_region.setStyle(style_hidden);
	bounds_city.setStyle(style_hidden);

	for(var i=0; i<results.length; i++){
		var bounds_converted = undefined;
		if(results[i].bounds !== undefined){
			bounds_converted = [
				[results[i].bounds[1],results[i].bounds[0]]
				,[results[i].bounds[3],results[i].bounds[2]]
			];
		}
		if(results[i].type === 'country'){
			display_country.text(results[i].name);
			if(bounds_converted !== undefined){
				bounds_country.setBounds(bounds_converted);
				bounds_country.setStyle(style_country);
			}
		}
		if(results[i].type === 'province'){
			display_region.text(results[i].name);
			if(bounds_converted !== undefined){
				bounds_region.setBounds(bounds_converted);
				bounds_region.setStyle(style_region);
			}
		}
		if(results[i].type === 'city'){
			display_city.text(results[i].name);
			if(bounds_converted !== undefined){
				bounds_city.setBounds(bounds_converted);
				bounds_city.setStyle(style_city);
			}
		}
	}
}

function geocoderSelectHandler(input){
//	console.log('geoCoderSelectHandler',input.data[0]);
	you.setLatLng(input.data[0]);
	displayResults(input.data);
	display_latitude.val(input.data[0].lat);
	display_longitude.val(input.data[0].lon);
}

function geocoderFoundHandler(input){
//	console.log('geocoderFoundHandler',input);
	you.setLatLng(input.latlng);
	displayResults(input.results[0]);
	display_latitude.val(input.latlng[0]);
	display_longitude.val(input.latlng[1]);
}

var geocoder = L.mapbox.geocoder(mapboxString);
map = L.mapbox.map('map', mapboxString, {zoom:2, center:[0,0], minZoom:1})
	.addControl(
		L.mapbox.geocoderControl(mapboxString, {})
		.on('select',geocoderSelectHandler)
		.on('found',geocoderFoundHandler)
	);


you = L.marker([0,0],{
	draggable:true
}).addTo(map);

you.on('dragend',function(event){
	var latlng = event.target.getLatLng();
	reverseGeocode(latlng);
	display_latitude.val(latlng.lat);
	display_longitude.val(latlng.lng);
});

bounds_country = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);
bounds_region = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);
bounds_city = L.rectangle([[0,0],[0,0]], style_hidden).addTo(map);

$(document).ready(function(){
	var latlng = [
		display_latitude.val(),
		display_longitude.val()
	];
	reverseGeocode({
		lat: latlng[0]
		,lng: latlng[1]
	});
  you.setLatLng(latlng);
	map.setView(latlng);
});
