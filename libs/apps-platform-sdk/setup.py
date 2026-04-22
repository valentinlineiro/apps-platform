from setuptools import setup, find_packages

setup(
    name="apps-platform-sdk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "flask>=3.0",
        "flask-cors>=4.0",
    ],
    extras_require={
        "postgres": ["psycopg2-binary>=2.9"],
        "migrations": ["alembic>=1.13"],
    },
)
