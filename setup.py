from distutils.core import setup
setup(
    name = "django-jython",
    version = "0.9",
    packages = ['doj',
                'doj.backends',
                'doj.backends..zxjdbc',
                'doj.backends..zxjdbc.postgresql',
                'doj.management',
                'doj.management.commands'],
    package_data = {'doj.management.commands':  ['war_skel/application.py',
                                                 'war_skel/WEB-INF/web.xml',
                                                 'war_skel/WEB-INF/lib/*',
                                                 'war_skel/WEB-INF/lib-python/README']},
    # metadata for upload to PyPI
    author = "Leonardo Soto M.",
    author_email = "leo.soto@gmail.com",
    description = "Database backends and management commands, for development under Django/Jython",
    license = "BSD",
    keywords = "django jython database java",
    url = "http://code.google.com/p/django-jython/"
)
