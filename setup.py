from setuptools import setup, find_packages

from aws import __version__

requirements = []
with open('requirements.txt') as f:
    requirements = [r for r in f.read().splitlines() if not r.startswith('-')]

setup(
    name='aws',
    version=__version__,
    license='GPLv3+',
    author='Joel Dubowy',
    author_email='jdubowy@gmail.com',
    packages=find_packages(),
    scripts=[
        'bin/ec2-execute',
        'bin/ec2-initialize',
        'bin/ec2-launch',
        'bin/ec2-network',
        'bin/ec2-reboot',
        'bin/ec2-resources',
        'bin/ec2-shutdown',
        'bin/elb-manage',
        'bin/s3-download',
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3.7",
        "Operating System :: POSIX",
        "Operating System :: MacOS"
    ],
    package_data={},
    url='https://github.com/pnwairfire/aws',
    description='Utilities for managin AWS resources.',
    install_requires=requirements,
    dependency_links=[
        "https://pypi.airfire.org/simple/afscripting/"
    ],
    tests_require=[]
)
