import unittest
import os

class WarCommandTestCase(unittest.TestCase):
    def testWarDontFailWhenUsingAppsFromSamePackage(self):
        cmdline = ('cd %s/apps_from_same_package/project;'
                   'JYTHONPATH=..:$JYTHONPATH jython manage.py war' %
                   os.path.abspath(os.path.dirname(__file__)))
        self.assertEqual(0, os.system(cmdline))

    def testWarDontFailWithOverlappingMedia(self):
        cmdline = ('cd %s/overlapping_media_url_and_admin_media;'
                   'JYTHONPATH=..:$JYTHONPATH jython manage.py war' %
                   os.path.abspath(os.path.dirname(__file__)))
        self.assertEqual(0, os.system(cmdline))

    def testWarFailIfAdminMediaAndMediaRootAreTheSame(self):
        cmdline = ('cd %s/same_media_root_and_admin_media_prefix;'
                   'JYTHONPATH=..:$JYTHONPATH jython manage.py war' %
                   os.path.abspath(os.path.dirname(__file__)))
        self.assertEqual(1, os.system(cmdline))
