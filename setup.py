from setuptools import setup, find_packages
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()
setup(
    name = 'scrub',
    version = '0.0.1',
    author = 'Paweł Marzec',
    author_email = 'pm@eoln.eu',
    license = 'GNU GPLv3',
    description = 'Glassnode scrapping tool',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://github.com/eoln/scrub',
    py_modules = ['scrub', 'src'],
    packages = find_packages(),
    install_requires = [requirements],
    python_requires='>=3.8',
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
    entry_points = '''
        [console_scripts]
        scrub=scrub:cli
    '''
)