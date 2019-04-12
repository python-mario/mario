import re

import setuptools

with open("requirements.in") as f:
    INSTALL_REQUIRES = f.read().splitlines()


setuptools.setup(
    name="pype",
    version="0.0.83",
    description="An example package. Generated with cookiecutter-pylibrary.",
    long_description=open("README.rst").read(),
    author="pype contributors",
    author_email='pype@example.com',
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    url='http://example.com',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Utilities",
    ],
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    python_requires=">=3.7",
    install_requires=INSTALL_REQUIRES,
    entry_points={
        "console_scripts": ["pype = pype.cli:cli"],
        "pype_plugins": ["basic = pype.plugins"],
    },
)
