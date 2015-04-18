=======================
MySQL DB Anonymization
=======================

Mozillians uses the production database for testing on stage and dev.
We provide a script to anonymize a  database to remove some
personal information for stage, and all personal information for dev.

#. Using the script::

    $ cd scripts/mysql-anonymize
    $ python anonymize.py anonymize_dev.yml > anon.sql
    $ mysql < anon.sql


   .. note::

      Make sure your database is named ``mozillians``. If it isn't, you can change
      the name in the .yml file you are using, it's clearly noted on the second line
      of each of the .yml configuration files.
