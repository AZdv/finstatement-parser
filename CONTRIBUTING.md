# Contributing to Financial Statement Parser

Thank you for your interest in contributing to the Financial Statement Parser project! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful, inclusive, and considerate in your interactions with other contributors.

## How Can I Contribute?

### Reporting Bugs

If you encounter a bug, please create an issue on our GitHub repository with the following information:

- A clear, descriptive title
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Screenshots or error messages (if applicable)
- Environment information (OS, Python version, etc.)

### Suggesting Enhancements

We welcome suggestions for new features or improvements. Please create an issue with:

- A clear, descriptive title
- A detailed description of the proposed enhancement
- Any relevant examples or use cases
- If possible, a rough implementation plan

### Adding Support for New Institutions

One of the most valuable contributions is adding support for new financial institutions. Here's how:

1. Create sample statement patterns (with sensitive data anonymized)
2. Implement institution-specific pattern recognition
3. Add comprehensive tests
4. Update documentation to list the new institution

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`
3. Make your changes
4. Run tests
5. Submit a pull request with a clear description of the changes

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/azdv/finstatement.git
   cd finstatement
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run tests:
   ```bash
   pytest
   ```

## Coding Standards

- Follow PEP 8 style guidelines
- Write docstrings for all public functions and classes
- Add type hints where appropriate
- Include comprehensive comments for complex logic
- Write unit tests for new features

## Testing Guidelines

- Write tests for all new features and bug fixes
- Anonymize any sample statements used in tests
- Test with a variety of PDF formats and layouts
- Consider edge cases and malformed inputs

## Documentation

- Update README.md with any new features or changes
- Add examples for significant new functionality
- Document limitations and known issues

## Review Process

Pull requests will be reviewed by project maintainers. We may suggest changes or improvements before merging.

## Attribution

Contributors will be acknowledged in the project's CONTRIBUTORS.md file.

## Contact

If you have questions or need help, please reach out to the project maintainers at info@azdv.co.

Thank you for your contributions!

---

<div align="center">
  <sub>Maintained by <a href="https://azdv.co">AZdev</a> - FinTech Innovation Execution Leaders</sub>
</div>
