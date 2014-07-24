// create base map
var map = L.map('map')
    .setView([0, 0], 1)
    .addLayer(L.mapbox.tileLayer('fabmud.i23cd7kk', {
        detectRetina: true,
        maxZoom: 5,
        minZoom: 1,
    }));

// add open street map attribution
map.attributionControl.addAttribution(
    '© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
);

var clusters = L.markerClusterGroup({
    showCoverageOnHover: false,
    iconCreateFunction: function(cluster) {
        return new L.DivIcon({
            iconSize: L.point(40,40),
            iconAnchor: L.point(25,25),
            className: 'moz-marker-cluster',
            html: cluster.getChildCount()
        });
    }
});

$(document).ready(function(){
var addressPoints = JSON.parse( document.getElementById('geodata').text );
console.log('map',map);
console.log('address points',addressPoints);

for (var i = 0; i < addressPoints.length; i++) {
    var labelText = addressPoints[i].labelText;
    var icon = L.icon({
        iconUrl: addressPoints[i].photo,
        iconRetinaUrl: addressPoints[i].photo2x,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        className: 'moz-marker-single'
    });
    var marker = L.marker(new L.LatLng(addressPoints[i].lat, addressPoints[i].lng), { title:labelText, icon:icon });
    console.log(marker);
    marker.bindPopup(labelText);
    clusters.addLayer(marker);
}

map.addLayer(clusters);
});