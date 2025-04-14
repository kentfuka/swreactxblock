swreactxblock
=============

The StepWise xBlock for the edX LMS platform, using React.js for its UI

HOW TO WORK DEV CYCLE
---------------------

The edX documentation on setting up a dev environment with the xBlock
SDK has two major missing steps. In section 3.2.3, you'll need to add
these two commands at step 0 and 3.5:

0. ``mkdir var`` The var directory needs to exist or the manage.py
   commands will fail when they try to write to their log files which
   they expect to be in a var directory.

1. 5 ``make install`` After you run the
   ``pip install -r requirements/base.txt`` command, you need to run
   ``make install`` or the test page UI will crash with an error about
   ``PluginMissingError: vertical_demo``

2. ``pip install xblock-utils`` As far as I can tell, python doesnt have
   anything equivalent to JavaScript/NPM's package.json file which
   stores references to exteral libraries when you do an
   ``npm install the_package`` so that the next developer can simply run
   ``npm install`` and get them all loaded. So we have to do it manually
   when setting up our xblock dev environment with this command.

