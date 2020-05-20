#!/usr/bin/env python
"""The setup script."""

from setuptools import find_packages, setup

with open('README.md') as f:
    readme = f.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

with open('requirements.txt') as requirements_file:
    requirements = [l.strip() for l in requirements_file]

with open('requirements_dev.txt') as test_requirements_file:
    test_requirements = [l.strip() for l in test_requirements_file]

setup_requirements = ['setuptools >= 38.6.0', 'twine >= 1.11.0']

extras = ["geopandas", "pandas", "shapely", "keplergl_cli"]
extra_reqs = {
    "docs": ["mkdocs", "mkdocs-material"],
    "cli": ["click", *extras],
    "extras": extras
}

# yapf: disable
setup(
    author="Kyle Barron",
    author_email='kylebarron2@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Create mosaicJSON for Landsat imagery",
    entry_points={
        'console_scripts': [
            'landsat-cogeo-mosaic=landsat_cogeo_mosaic.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords=['landsat', 'cogeo', 'geotiff'],
    name='landsat_cogeo_mosaic',
    packages=find_packages(include=['landsat_cogeo_mosaic', 'landsat_cogeo_mosaic.*']),
    setup_requires=setup_requirements,
    extras_require=extra_reqs,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/kylebarron/landsat-cogeo-mosaic',
    version='0.1.1',
    zip_safe=False,
)
