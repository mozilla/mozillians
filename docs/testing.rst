=========
 Testing
=========

Test Coverage
-------------

You can combine `nose` testing with the `coverage` module to get the
code coverage of the tests. To get a coverage report for the 'users'
package run::

  $ coverage run --omit='*migrations*' manage.py test --noinput
  $ coverage xml --omit='*migrations*' $(find mozillians -name '*.py')

Then visit `htmlcov/index.html` to get the coverage results.
