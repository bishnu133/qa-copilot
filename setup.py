from setuptools import setup, find_packages

# Read requirements
with open("requirements/base.txt") as f:
    base_requirements = f.read().splitlines()

setup(
    name="qa-copilot",
    version="0.1.0",
    author="QA Copilot Contributors",
    description="Modular AI-powered QA automation tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/qa-copilot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=base_requirements,
    extras_require={
        "ai": ["ollama", "transformers", "torch"],
        "ocr": ["easyocr", "opencv-python"],
        "dev": ["pytest", "black", "flake8", "mypy"],
    },
    entry_points={
        "console_scripts": [
            "qa-copilot=qa_copilot.cli:main",
        ],
    },
)
