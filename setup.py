from setuptools import setup, find_packages
setup(
    name = "django-jython",
    version = "0.9",
    packages = find_packages(),
    # metadata for upload to PyPI
    author = "Leonardo Soto M.",
    author_email = "leo.soto@gmail.com",
    description = "Database backends and management commands, for development under Django/Jython",
    license = "BSD",
    keywords = "django jython database java",
    url = "http://code.google.com/p/django-jython/"
)
