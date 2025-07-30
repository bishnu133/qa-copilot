# QA-Copilot 🤖

A modular, AI-powered QA automation tool that works offline and requires no scripting knowledge.

## Features

- 🔍 **Smart Element Detection**: Find UI elements using natural language
- 📝 **BDD Generation**: Convert plain English to executable test scenarios
- 🚀 **Scriptless Automation**: Execute tests without writing code
- 🔧 **Failure Analysis**: AI-powered root cause analysis
- 📊 **Smart Reporting**: Automated bug reports and test coverage

## Installation

```bash
# Install core only
pip install qa-copilot-core

# Install specific modules
pip install qa-copilot-detector  # Element detection only
pip install qa-copilot-bdd       # BDD generation only

# Install all modules (no AI)
pip install qa-copilot

# Install with AI capabilities
pip install qa-copilot[ai]
```

## Quick Start

```python
from qa_copilot.detector import ElementDetector
from qa_copilot.executor import TestExecutor

# Find elements using natural language
detector = ElementDetector()
element = detector.find("Click on the blue Login button")

# Execute tests without scripting
executor = TestExecutor()
executor.run("features/login.feature")
```

## Modules

Each module works independently:

- **detector**: Find UI elements using multiple strategies
- **bdd**: Generate BDD scenarios from plain English
- **executor**: Run tests without writing code
- **analyzer**: Analyze failures and suggest fixes
- **datagen**: Generate test data
- **reporter**: Create reports and bug tickets

## Documentation

See the [docs](docs/) directory for detailed documentation.

## License

[TBD]
