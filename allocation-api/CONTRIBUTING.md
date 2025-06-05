# Contributing to Order Allocation API

Thank you for your interest in contributing to the Order Allocation API project!

## Getting Started

1. **Fork the repository** and clone your fork
2. **Set up the development environment**:
   ```bash
   cd allocation-api
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```
3. **Copy the environment template**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes
- Follow the existing code structure
- Add tests for new functionality
- Update documentation as needed

### 3. Code Style
We use Black, Flake8, and MyPy for code quality:
```bash
# Format code
black app/

# Check linting
flake8 app/

# Check types
mypy app/
```

### 4. Run Tests
```bash
# Basic functionality tests
python test_setup.py
python test_allocation_engines.py
python test_api_endpoints.py

# Full test suite (when implemented)
pytest tests/
```

### 5. Commit Your Changes
Write clear, descriptive commit messages:
```
feat: add order modification endpoint
fix: correct min denomination handling in pro-rata engine
docs: update API documentation for new endpoints
test: add tests for allocation preview
refactor: simplify Aladdin client retry logic
```

### 6. Push and Create a Pull Request
```bash
git push origin feature/your-feature-name
```
Then create a PR on GitHub with:
- Clear description of changes
- Link to any related issues
- Screenshots if UI changes
- Test results

## Code Standards

### Python Style Guide
- Follow PEP 8
- Use type hints where possible
- Maximum line length: 88 (Black default)
- Use descriptive variable names

### API Design
- RESTful principles
- Consistent error responses
- Comprehensive input validation
- Clear endpoint documentation

### Testing
- Write tests for all new features
- Maintain test coverage above 80%
- Include both unit and integration tests
- Mock external dependencies

### Documentation
- Update docstrings for new functions
- Update API documentation for new endpoints
- Include examples in documentation
- Keep README current

## Project Structure

```
app/
├── api/          # API endpoints
├── core/         # Core utilities
├── services/     # Business logic
├── models/       # Database models
├── schemas/      # Request/response schemas
└── utils/        # Helper utilities
```

### Adding a New API Endpoint

1. Create endpoint in appropriate `api/` module
2. Add request/response models using Flask-RESTX
3. Implement business logic in `services/`
4. Add authentication/authorization as needed
5. Write tests for the endpoint
6. Update API documentation

### Adding a New Allocation Engine

1. Create new module in `services/allocation_engines/`
2. Inherit from `BaseAllocationEngine`
3. Implement `allocate()` method
4. Add engine to factory in `factory.py`
5. Write comprehensive tests
6. Document algorithm and parameters

## Common Tasks

### Adding a New Dependency
```bash
pip install new-package
pip freeze > requirements.txt
# Manually clean up requirements.txt to remove dev dependencies
```

### Debugging
- Use the structured logger:
  ```python
  from app.core.logging import get_logger
  logger = get_logger(__name__)
  logger.info("Debug message", extra={"data": value})
  ```
- Check logs in JSON format for production
- Use debugger with Flask debug mode

### Performance Optimization
- Profile code before optimizing
- Use async operations for I/O
- Implement caching where appropriate
- Consider database query optimization

## External Services

### Aladdin API
- Test with mock data when credentials unavailable
- Respect rate limits (100/minute)
- Handle errors gracefully
- Cache responses appropriately

### Snowflake
- Use connection pooling
- Optimize queries for large datasets
- Handle connection failures gracefully

## Security Considerations

- Never commit secrets or credentials
- Validate all user inputs
- Use parameterized queries
- Implement proper authorization
- Keep dependencies updated

## Getting Help

- Check existing issues on GitHub
- Review the architecture documentation
- Look at existing code for patterns
- Ask questions in pull requests

## Code Review Process

Pull requests will be reviewed for:
- Code quality and style
- Test coverage
- Documentation updates
- Security considerations
- Performance impact
- API consistency

## Release Process

1. Ensure all tests pass
2. Update CHANGELOG.md
3. Update version numbers
4. Create release notes
5. Tag the release

## Recognition

Contributors will be recognized in:
- Release notes
- Project documentation
- GitHub contributors page

Thank you for contributing!