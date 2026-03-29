# Contributing to OpenHarness

Thank you for your interest in contributing to OpenHarness! We are building the ultimate 24/7 autonomous AI framework, and community contributions are essential to making our AI agents even smarter and more robust.

## Code of Conduct

By participating in this project, you agree to maintain a welcoming, inclusive, and harassment-free environment for everyone. 

## How Can I Contribute?

### 1. Reporting Bugs
If you find a bug in the framework (e.g., `harness_boot.py` fails, state persistence issues in `heartbeat.md`), please open an issue on GitHub. Include:
- A clear description of the problem
- Steps to reproduce the behavior
- Your OS and Agent version
- Relevant logs or error messages

### 2. Suggesting Enhancements
Have an idea for a new feature or an improvement to the Harness Engineering implementation? Open an issue and tag it as an `enhancement`. Describe how it aligns with the six core components of Harness Engineering.

### 3. Pull Requests
We welcome PRs for bug fixes, new features, and documentation improvements.
1. Fork the repository and create your branch from `main`.
2. Ensure your code follows the existing style and conventions.
3. If you've added code that should be tested, add tests.
4. Update the documentation if you change any scripts or templates.
5. Issue that PR!

## Development Setup

1. Clone the repository into your Agent workspace:
   ```bash
   git clone https://github.com/your-org/OpenHarness.git ~/.agent/workspace/harness
   ```
2. Test the Python scripts locally using the `--dry-run` flags where available.
3. Ensure your changes do not break the core `mission.md` and `heartbeat.md` lifecycle.

## Harness Engineering Principles

When contributing, please keep the core philosophy in mind:
> "Harness Engineering is not about post-mortem reviews, but about solidifying boundaries, aesthetics, and risk awareness into mechanical rules that can be continuously executed."

Do not introduce complex abstractions if a simple, explicit file-based state works. The goal is transparency and reliability.

Happy coding, and let's keep the agents working!
