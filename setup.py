from setuptools import setup, find_packages

setup(
    name="queuectl",
    version="0.1.0",
    author="Dhivya",
    description="A CLI-based background job queue system.",
    packages=find_packages(),
    install_requires=["click"],
    entry_points={
        "console_scripts": [
            "queuectl=queuectl.cli:main",
        ],
    },
    python_requires=">=3.8",
)
