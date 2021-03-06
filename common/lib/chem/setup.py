from setuptools import setup

setup(
    name="chem",
    version="0.1.1",
    packages=["chem"],
    install_requires=[
        "pyparsing==2.0.7",
        "numpy==1.16.6",
        "scipy==0.14.0",
        "nltk==2.0.6",
    ],
)
