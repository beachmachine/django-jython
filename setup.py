# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name='django-jython',
    version='1.7.0a1',
    packages=[
        'doj',
        'doj.db',
        'doj.db.backends',
        'doj.db.backends.postgresql',
        'doj.db.backends.mysql',
        'doj.db.backends.sqlite',
        'doj.db.backends.mssql',
    ],
    package_data={
        'doj.management.commands': []
    },
    # metadata for upload to PyPI
    author=u"Josh Juneau",
    author_email=u"juneau001@gmail.com",
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
