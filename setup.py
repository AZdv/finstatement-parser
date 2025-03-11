from setuptools import setup, find_packages

setup(
    name="finstatement",
    version="0.1.0",
    description="Financial statement PDF parser",
    author="AZdev",
    author_email="info@azdv.co",
    url="https://github.com/azdv/finstatement-parser",
    packages=find_packages(),
    install_requires=[
        "PyPDF2>=2.0.0",
        "reportlab>=3.6.0",  # For sample generator
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Office/Business :: Financial",
    ],
)
