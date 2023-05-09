"""Python setup.py for project_name package"""
from setuptools import find_packages, setup

_long_description = ""

try:
    with open('README.md', 'rt') as f:
        _long_description = f.read()
except FileNotFoundError:
    pass

setup(
    name="planning_center_backend",
    version='0.1.0',
    description="Python request bindings to the Planning Center website",
    # url="https://github.com/griffperry/planning_center_bot",
    long_description=_long_description,
    long_description_content_type="text/markdown",
    author="Benjamin Davis",
    packages=find_packages('src', exclude=["tests", ".github"]),
    package_dir={"": 'src'},
    install_requires=[
        'requests',
        'beautifulsoup4',
        'msgspec',
        'pandas',
        'cachetools',
    ],
    extras_require={"test": ['pytest', 'keyring']},
)
