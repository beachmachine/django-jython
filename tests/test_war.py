import unittest
import os

class WarCommandTestCase(unittest.TestCase):
    def testWarDontFailWhenUsingAppsFromSamePackage(self):
        cmdline = ('cd %s/apps_from_same_package/project;'
                   'JYTHONPATH=..:$JYTHONPATH jython manage.py war' %
                   os.path.abspath(os.path.dirname(__file__)))
        self.assertEqual(0, os.system(cmdline))
