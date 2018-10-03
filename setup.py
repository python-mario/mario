import os

import setuptools

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, 'README.rst'), 'r') as infile:
    long_description = infile.read()

setuptools.setup(
    name="python-pype",
    author='author',
    packages=setuptools.find_packages(),
    install_requires=[
        "click",
        "toolz",
        "attrs",
        "click_default_group",
        "parso",
        "twisted",
    ],
    entry_points={'console_scripts': ['pype=pype.app:cli']},
    include_package_data=True,
)
