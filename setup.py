from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in erpnext_workflow/__init__.py
from erpnext_workflow import __version__ as version

setup(
	name="erpnext_workflow",
	version=version,
	description="Erpnext Workflow",
	author="Midocean",
	author_email="Midocean@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
