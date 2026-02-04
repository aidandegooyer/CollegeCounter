# Contributing to College Counter

Thank you for your interest in contributing to College Counter! We welcome contributions from the community.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CollegeCounter.git
   cd CollegeCounter
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/aidandegooyer/CollegeCounter.git
   ```
4. **Follow the setup instructions** in the [README.md](README.md) to get your development environment running

## How to Contribute

### Reporting Bugs
- Check if the bug has already been reported in [Issues](https://github.com/aidandegooyer/CollegeCounter/issues)
- If not, create a new issue using the **Bug Report** template
- Provide as much detail as possible: steps to reproduce, expected behavior, actual behavior, screenshots, etc.

### Suggesting Features
- Check if the feature has already been requested
- Create a new issue using the **Feature Request** template
- Clearly describe the feature and its benefits

### Submitting Code Changes
1. Create an issue describing the change (if one doesn't exist)
2. Follow the development workflow below
3. Submit a pull request

## Development Workflow

### 1. Create a Branch
Create a feature branch from `main`:
```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Adding or updating tests
- `chore/description` - Maintenance tasks

### 2. Make Your Changes
- Write clean, maintainable code
- Follow the coding standards below
- Add tests if applicable
- Update documentation as needed

### 3. Test Your Changes
Ensure your changes work correctly:

**Backend:**
```bash
cd cc-backend/v1
uv run python manage.py test
```

**Frontend:**
```bash
cd cc-frontend/v1
npm run lint
npm run build
```

Test manually using the development servers (see README.md).

### 4. Commit Your Changes
Follow the commit guidelines below.

### 5. Push and Create a Pull Request
```bash
git push origin feature/your-feature-name
```
Then create a pull request on GitHub using the PR template.

## Coding Standards

### Python (Backend)
- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Maximum line length: 100 characters
- Use meaningful variable names

### TypeScript/React (Frontend)
- Follow the existing ESLint configuration
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use meaningful component and variable names
- Keep components focused and reusable

### General
- Write self-documenting code
- Add comments for complex logic
- Avoid hardcoding values - use configuration/constants
- Handle errors gracefully
- Don't commit commented-out code
- Don't commit console.log statements (unless for debugging utilities)

## Commit Guidelines

Write clear, descriptive commit messages:

### Format:
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

### Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, missing semicolons, etc.)
- `refactor:` - Code refactoring without changing functionality
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks, dependency updates

### Examples:
```
feat: add ELO ranking history chart

fix: resolve crash when loading team roster with missing players

docs: update installation instructions for PostgreSQL 18

refactor: extract match result parsing into separate utility function
```

### Guidelines:
- Use the imperative mood in the subject line ("add" not "added")
- Keep the subject line under 50 characters
- Capitalize the subject line
- Do not end the subject line with a period
- Separate subject from body with a blank line
- Wrap the body at 72 characters
- Use the body to explain what and why, not how

## Pull Request Process

1. **Ensure your code follows the coding standards** and all tests pass
2. **Update documentation** if you've changed functionality
3. **Fill out the pull request template** completely
4. **Link related issues** using keywords (e.g., "Closes #123" or "Fixes #456")
5. **Request review** from maintainers
6. **Address feedback** promptly and professionally
7. **Keep your PR focused** - one feature/fix per PR
8. **Squash commits** if requested before merging

### PR Requirements:
- All CI checks must pass
- At least one approval from a maintainer
- No merge conflicts
- Branch is up to date with main

## Questions?

If you have questions or need help:
- Check existing [Issues](https://github.com/aidandegooyer/CollegeCounter/issues) and [Discussions](https://github.com/aidandegooyer/CollegeCounter/discussions)
- Create a new discussion for general questions
- Reach out to [@aidandegooyer](https://github.com/aidandegooyer) (@aidanxi on Discord)

Thank you for contributing to College Counter! 🎮
