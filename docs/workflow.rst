.. _workflow:

============
Workflow
============

.. note::
    The Mozillians workflow might be daunting.  Ask for help in #mozillians on
    irc.mozilla.org.  jsocol, timw, or tallOwen will be happy to help.

This is our basic workflow for how features are born. It is what you need to
do to get code landed.

1. Start a new feature branch::

   Figure out what you want to work on by asking in IRC, finding an open bug in
   Bugzilla or find something small (CSS fix, or typo) that bothers you in the
   site and fix it.

   ::

    $ git checkout -b {{ new branch name }}

   .. seealso::
      `The git book: git branching
       <http://book.git-scm.com/3_basic_branching_and_merging.html>`_

2. Work on said feature and run tests::

    $ t

   or without vagrant:

   ::

    $ ./manage.py test -x --logging-clear-handlers --with-nicedots'

    .. note::
    You may run into issues with the database if you have added south migrations
    or if your database is out of sync. You can run ``td`` or
    ``FORCE_DB=True ./manage.py test -x --logging-clear-handlers --with-nicedots --noinput`` if you are having issues.

   If all the tests pass you are good to go! If you are working on a feature
   or a regression we will ask that you add your own tests. (Look for a test
   directory or a tests.py file in any of the apps.)

3. Commit your changes::

    We ask that your commit message reference a bug that it is fixing, a good
    subject line and a summary of what has changed in the body of the commit.

   .. seealso::
      `A note about git commit messages
       <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_

4. Submit a pull request::

    To get your code into the code base you will need to get it reviewed by one
    of the core devs. Submit a pull request on GitHub and ask for a review in
    the #mozillians or #commtools chanel.

    After a review, you may need to make changes to your code. If you are
    confused by the comments on your code ask the reviewer what they mean and
    they will gladly answer questions.

   .. seealso::
      `GitHub: Sending pull requests
       <http://help.github.com/send-pull-requests/>`_



