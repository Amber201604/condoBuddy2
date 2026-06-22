#!/usr/bin/env python
from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
    name="condobuddy2_erp",
    version="1.0.0",
    description="CondoBuddy2 Smart Community Platform - Frappe App",
    author="CondoBuddy Team",
    author_email="admin@condobuddy.ca",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
