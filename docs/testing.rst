=========
 Testing
=========

Testing Mozillians Code
-----------------------

* To run mozillians.org tests::

  $ ./manage.py test

* If you need a fresh test database::

  $ FORCE_DB=1 ./manage.py test

* To run all tests in a class::

  $ ./manage.py test mozillians.users.tests.test_models:UserProfileTests

* If you want to run a single test::

  $ ./manage.py test mozillians.users.tests.test_models:UserProfileTests.test_get_attribute_with_public_level

  to run only `test_get_attribute_with_public_level` test from the `UserProfileTests` class in the `mozillians/users/tests/test_models.py` test file.


Test Coverage
-------------

You can combine `nose` testing with the `coverage` module to get the
code coverage of the tests. To get a coverage report for the 'users'
package run::

  $ coverage run --omit='*migrations*' manage.py test --noinput
  $ coverage xml --omit='*migrations*' $(find mozillians -name '*.py')

Then visit `htmlcov/index.html` to get the coverage results.
