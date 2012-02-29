(function($){
    'use_strict';
    var endpoint = '/api/v1/contact/'

    _.mixin({
        starts_with : function(large, sub) {
            return (large.toLowerCase().indexOf(sub.toLowerCase()) === 0);
        }
    });

    // define our model (i.e. row).
    var Profile = Backbone.Model.extend({

        match: function(qtokens) {
            var tokens = this._tokens();
            return !(_.find(qtokens, function(qtoken) {
                return undefined === _.find(tokens, function(token){
                    return _.starts_with(token, qtoken);
                });
            }));
        },

        _tokens: function() {
            var attrs = this.attributes;
            var tokens = [];
            tokens.push(attrs.display_name.split(' '));
            tokens.push(attrs.email);
            tokens.push(attrs.ircname);

            // flatten and remove values that evaluate to false.
            return _.compact(_.flatten(tokens));
        }

    });

    var updated = null;
    // define our collection (i.e. table).
    var profiles_constructor = Backbone.Collection.extend({
        model: Profile,
        localStorage: new Store("Profiles"),
        sync: Backbone.sync,

        // Load our userdata from the server
        load: function() {
            app.Profiles._get_data(endpoint)
        },

        _set_updated: function(timestamp) {
            localStorage.setItem('Profiles-updated', timestamp)
        },

        _get_updated: function() {
            return localStorage.getItem('Profiles-updated')
        },

        _get_data: function(endpoint) {
            var context = this;
            var options = {};

            if (context._get_updated() !== null) {
                options = {'updated': context._get_updated()}
            }

            $.get(endpoint, options, function(data) {
                _.each(data.objects, function(contact){
                    model = app.Profiles.get(contact.id)
                    if (!(model)) {
                        app.Profiles.create(contact);
                    } else {
                        model.set(contact);
                    }
                });
                if (data.meta.previous === null) {
                    // If this is the first response let's note time updated
                    updated = data.updated;
                }
                if (data.meta.next !== null) {
                    // If there are more items in queue keep going
                    app.Profiles._get_data(data.meta.next);
                } else {
                    // If this is the last page, store the original response
                    // time
                    context._set_updated(updated);
                }
            });
        },

        // Performs a search. Looks for objects that match the query and
        // Returns them in no particular order.
        search: function(query) {
            var qtokens = this._qtokens(query);
            return _.filter(this.models, function(model) {
                return model.match(qtokens);
            });
        },

        // Tokenize the query
        _qtokens: function(query) {
            var qtokens = query.split(' ');
            return qtokens;
        }

    });

    // Create an instance of our collection
    app.Profiles = new profiles_constructor();
    // Load everything we have from local storage into memory
    app.Profiles.fetch();
})(jQuery);
