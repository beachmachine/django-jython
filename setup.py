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
        'doj.monkey',
        'doj.tests',
        'doj.tests.db',
        'doj.tests.db.migrations',
    ],
    package_data={
        'doj.management.commands': []
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
