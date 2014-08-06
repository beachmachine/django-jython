# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name='django-jython',
    version='1.7.0a1',
    packages=[
        'doj',
        'doj.db',
        'doj.db.backends',
        'doj.db.backends.mssql',
        'doj.db.backends.mysql',
        'doj.db.backends.postgresql',
        'doj.db.backends.sqlite',
        'doj.management',
        'doj.management.commands',
        'doj.monkey',
        'doj.tests',
        'doj.tests.db',
        'doj.tests.db.migrations',
        'doj.tests.monkey',
    ],
    package_data={
        'doj.management.commands': [
            'war_skel/wsgi.py.tmpl',
            'war_skel/WEB-INF/web.xml.tmpl',
            'war_skel/WEB-INF/lib/README',
            'war_skel/WEB-INF/lib/jruby-extras-fileservlet.jar',
            'war_skel/WEB-INF/lib-python/application_settings.py.tmpl',
            'war_skel/WEB-INF/lib-python/README',
        ],
    },
    # metadata for upload to PyPI
    author=u"Andreas Stocker",
    author_email=u"andreas@st0cker.at",
    description=u"Database backends and management commands, for development under Django/Jython",
    license=u"BSD",
    keywords=u"django jython doj database java",
    url=u"http://code.google.com/p/django-jython/",
    classifiers=[
        u"Development Status :: 3 - Alpha",
        u"Framework :: Django",
        u"Intended Audience :: Developers",
        u"License :: OSI Approved :: BSD License",
        u"Programming Language :: Python",
        u"Programming Language :: Java"
    ]
)
