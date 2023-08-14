import setuptools

# with open("README.md", "r", encoding="utf-8") as fh:
#     long_description = fh.read()

setuptools.setup(
    name="datahub-irods-ruleset",
    version="1.0.0",
    author="DataHub",
    author_email="datahub@maastrichtuniversity.nl",
    description="This repository contains the python iRODS server rule-set",
    long_description="TODO",
    long_description_content_type="text/markdown",
    url="https://github.com/MaastrichtUniversity/irods-ruleset",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "dh-python-irods-utils @ git+https://github.com/MaastrichtUniversity/dh-python-irods-utils.git@v1.1.1#egg=dh-python-irods-utils",
        "cryptography",
        "jsonschema==3.0.2",
        "pyrsistent==0.16.1",
        "requests==2.25.1",
        "requests_cache==0.5.2",
        "elasticsearch==7.17.6",
        "pytest",
    ],
    # tests_requires=["pytest"],
)
