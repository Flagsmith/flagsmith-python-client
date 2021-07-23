from setuptools import setup

with open("Readme.md", "r") as readme:
    long_description = readme.read()

setup(
    name="flagsmith",
    version="2.0.0",
    packages=["flagsmith"],
    description="Flagsmith Python SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Bullet Train Ltd",
    author_email="supoprt@flagsmith.com",
    license="BSD3",
    url="https://github.com/Flagsmith/flagsmith-python-client",
    keywords=["feature", "flag", "flagsmith", "remote", "config"],
    install_requires=[
        "requests>=2.19.1",
    ],
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
