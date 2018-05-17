from setuptools import setup

setup(
    name="perceptual_hashing",
    version="0.1",
    packages=['perceptual_hashing'],
    scripts=['bin/run_experiments'],
    install_requires=['docutils>=0.3'],
    package_data={'': ['*.txt', '*.rst', '*.md']},
    test_suite='nose.collector',
    tests_require=['nose', 'mock'],
)
