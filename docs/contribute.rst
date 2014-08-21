.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _contribute:

=================
How to Contribute
=================

Thank you for your interest in contributing to Mozillians! There are always bugs to file; bugs to fix in code; improvements to be made to the documentation; and more.

The below instructions are for software developers who want to work on Mozillians code.

Git workflow
------------
When you want to start contributing, you should :doc:`follow the installation instructions </installation-virtualenv>`, then...

#.  (Optional) Set your cloned fork to track upstream changes (changes to the main repository), then fetch and merge changes from the upstream branch::

    $ git remote add --track master upstream git://github.com/mozilla/mozillians
    $ git fetch upstream
    $ git merge upstream/master

#. Set up a branch for a particular set of changes and switch to it::

    $ git branch my_branch
    $ git checkout my_branch

#. Commit changes to the code!

#. Code!

#. Lint the code::

    $ flake8 mozillians

   and fix any errors.

#. Run the tests::

    $ ./manage.py test

   and make sure that all tests pass.

   Learn more about :doc:`testing </testing>`.

#. Commit changes to the code!

#. When you're done, figure out how many commits you've made::

    $ git log

#. Squash all those commits into a single commit that has a `good git commit message`_. (Example assumes you made 4 commits)::

    $ git rebase -i HEAD~4

#. Use the interactive editor that pops up to pick/squash your commits::

    pick 01d1239 [fix bug 893291] Make it go to 11
    squash 32as32p added the library and made some minor changes
    squash 30ame3z build the template
    squash 91pcla8 ugh fix a semicolon bug in that last commit

#. Push your changes to your fork::

    $ git push origin my_branch

#. Issue a `pull request`_ on GitHub

#. Wait to hear from one of the core developers

If you're asked to change your commit message, you can amend the message and force commit::

  $ git commit --amend
  $ git push -f origin my_branch

If you need more Git expertise, a good resource is the `Git book`_.

Templates
---------

Mozillians.org uses `Jinja <http://jinja.pocoo.org/docs/>`_ templates, which
are similar to Django templates but have some differences.

Some helpers are available in all Jinja templates in Mozillians.org.

display_context
~~~~~~~~~~~~~~~

Return a marked-up chunk of content containing the items
in the template context, if ``settings.DEBUG`` is True.
Otherwise returns an empty string.

By default, callables are omitted. Pass include_callables=True
to include them.

The format of the result is::

        <dl class="jinja-context">
          <dt>key</dt><dd>value</dd>
          <dt>key</dt><dd>value</dd>
          ...
        </dl>

``repr`` is applied to the values to format them.

Example usage::

        {{ display_context() }}

        {{ display_context(include_callables=True) }}

get_context
~~~~~~~~~~~
Provide access to the Jinja :class:`Context` object in case
you want to do more complicated things with it. Typically,
``display_context()`` is easier to use.

If ``settings.DEBUG`` is not True, returns an empty dictionary.

Example usage::

    {% set context=get_context() %}
    {% for k, v in context|dictsort %}
        {% if not is_callable(v) %}
            {{ k }}: {{ v }}<br/>
        {% endif %}
    {% endfor %}

is_callable
~~~~~~~~~~~

Return True if thing is callable.

See get_context() for example usage.


Server architecture
-------------------
**Dev**

- *URL:* http://mozillians-dev.allizom.org/
- *Deploy:* Automatic after code merge, if unit tests pass

**Stage**

- *URL:* http://mozillians.allizom.org/
- *Deploy:* Manual (Chief)

**Production**

- *URL:* http://www.mozillians.org/
- *Deploy:* Manual (Chief)

You can check the currently deployed git commit by checking https://www.mozillians.org/media/revision.txt.

Pushing to production
---------------------
In 2013 Mozillians code is released on Thursdays, after QA and developers agree that code is ready to push to production. The list of code scheduled for any particular release is here: https://wiki.mozilla.org/Mozillians#Releases

What to work on
---------------
Mozillians development follows a `schedule`_ and a `roadmap`_ managed by the `Mozillians product and development team`_. Bugs that the team has committed to work on are generally given a *target milestone* and are *assigned* to a developer. Other bugs are fair game; but they're not all aligned with the product's current evolution. So if you are not familiar with the project and its roadmap, you may want to find one of the core team in IRC and ask before working on a particular bug. 

- `All outstanding bugs`_ 
- `Good first bugs`_ 
- `Submit a bug`_ 

.. _Git book: http://git-scm.com/book
.. _good git commit message: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
.. _Mozillians product and development team: https://wiki.mozilla.org/Mozillians#Team
.. _schedule: https://wiki.mozilla.org/Mozillians#Schedule
.. _roadmap: https://wiki.mozilla.org/Mozillians/RoadMap
.. _All outstanding bugs: https://bugzilla.mozilla.org/buglist.cgi?product=Community%20Tools;component=Phonebook;resolution=---;list_id=5645789
.. _Good first bugs: https://bugzilla.mozilla.org/buglist.cgi?list_id=5667806;classification=Other;status_whiteboard_type=allwordssubstr;query_format=advanced;status_whiteboard=mentor;bug_status=NEW;component=Phonebook;product=Community%20Tools
.. _pull request: https://github.com/YOUR_USERNAME/mozillians/pull/new/master
.. _submit a bug: https://bugzilla.mozilla.org/enter_bug.cgi?product=Community%20Tools&component=Phonebook&status_whiteboard=&target_milestone=---&version=other
