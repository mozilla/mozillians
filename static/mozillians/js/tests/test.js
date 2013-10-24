(function(){
    var user = {
        'display_name': 'Matt MacPherson',
        'website': 'http://lonelyvegan.com/',
        'id': '133713371337',
        'email': 'somebody@lonelyvegan.com'
    };

    var clear = function() {
        _.each(_.clone(app.Profiles.models),function(model){
            model.destroy();
        });

        localStorage.clear();
    };

    test('Local Storage Exists', function() {
        ok(localStorage);
    });

    test('Add Profile, find in localStorage', function() {
        clear();
        ok(!app.Profiles.get(user.id));
        ok(app.Profiles.create(user));
        ok(app.Profiles.get(user.id));
        ok(localStorage.getItem('Profiles-'+user.id));
    });

    test('Create some users, search for one', function() {
        clear();
        app.Profiles.create(user);
        for (var i = 0; i < 5; i++) {
            robot = {
                'display_name': 'robot'+i,
                'website': 'http://lonelyvegan.com/',
                'id': '133713371337'+i,
                'email': 'hello@lonelyvegan.com'
            };
            app.Profiles.create(robot);
        }
        equal(app.Profiles.length, 6);

        equal(app.Profiles.search('matt')[0].attributes.display_name,
              user.display_name);
    });

})();
