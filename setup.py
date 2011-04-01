from distutils.core import setup
setup(
    name = "django-jython",
    version = "1.3.0b1",
    packages = ['doj',
                'doj.backends',
                'doj.backends.zxjdbc',
                'doj.backends.zxjdbc.postgresql',
                'doj.backends.zxjdbc.oracle',
                'doj.backends.zxjdbc.mysql',
                'doj.backends.zxjdbc.mysql.constants',
                'doj.backends.zxjdbc.sqlite3',
                'doj.backends.zxjdbc.mssql2k',
                'doj.management',
                'doj.management.commands',
                'doj.test',
                'doj.test.xmlrunner'],
    package_data = {
        'doj.management.commands':  ['war_skel/application.py',
                                     'war_skel/WEB-INF/web.xml',
                                     'war_skel/WEB-INF/lib/*',
                                     'war_skel/WEB-INF/lib-python/README']},
    # metadata for upload to PyPI
    author = "Josh Juneau",
    author_email = "juneau001@gmail.com",
    description = "Database backends and management commands, for development under Django/Jython",
    license = "BSD",
    keywords = "django jython database java",
    url = "http://code.google.com/p/django-jython/",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Java"
    ]
)
