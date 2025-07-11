from setuptools import setup, find_packages

setup(
    name='crypto_signals_bot',
    version='0.1.0',
    packages=find_packages(where='.'),
    install_requires=[
        line.strip() for line in open('requirements.txt').readlines()
    ],
)


