from setuptools import setup, find_packages

setup(
    name="regex-composer",
    version="0.0.1",
    package_dir={"": "."},
    packages=find_packages(),
    zip_safe=False,
    install_requires=[],
    extras_require={
        "dev": [
            "pytest==6.1.0",
            "flake8==3.8.4",
            "pytest-cov==2.10.1"
        ]
    },
    include_package_data=True,
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 2 - Pre-Alpha",
    ],
)
