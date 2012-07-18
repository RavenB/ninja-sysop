import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'pyramid_debugtoolbar',
    'waitress',
    'deform',
    'deform_bootstrap',
    'passlib',
    'webhelpers',
    'ipaddr',
    'paste',
    ]

setup(name='ninja-sysop',
      version='0.0',
      description='ninja-sysop',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="ninjasysop",
      entry_points = """\
      [paste.app_factory]
      main = ninjasysop:main
      [ninjasysop.plugins]
      dhcpd = plugins.dhcpd.dhcpd:Dhcpd
      bind9 = plugins.bind9.bind9:Bind9
      """,
      )

