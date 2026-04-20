from setuptools import setup, find_packages

setup(
    name="apps-platform-sdk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "flask>=3.0",
    ],
)
