# Test Suite Documentation

This directory contains a comprehensive test suite for the chat application API, organized following best practices and testing pyramid principles.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and test configuration
├── unit/                       # Unit tests (fast, isolated)
│   ├── services/              # Service layer unit tests
│   │   ├── test_chat_service.py
│   │   ├── test_ask_service.py
│   │   ├── test_vote_service.py
│   │   ├── test_auth_service.py
│   │   ├── test_session_service.py
│   │   └── test_response_generator.py
│   └── schemas/               # Schema validation tests
├── integration/               # Integration tests (medium speed)
│   └── api/                  # API endpoint integration tests
│       └── test_chat_endpoints.py
├── e2e/                      # End-to-end tests (slower, complete workflows)
│   └── test_complete_workflows.py
├── fixtures/                 # Test data and fixtures
└── README.md                # This file
```

## Test Types

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 1 second per test)
- **Scope**: Single functions/methods with mocked dependencies
- **Coverage**: Each service class has comprehensive unit tests

#### Service Tests
- `test_chat_service.py`: Tests ChatService functionality (chat operations only)
- `test_ask_service.py`: Tests AskService functionality (ask operations only)
- `test_vote_service.py`: Tests VoteService functionality (voting/feedback only)
- `test_auth_service.py`: Tests AuthService functionality (authentication only)
- `test_session_service.py`: Tests SessionService functionality (session management only)
- `test_response_generator.py`: Tests ResponseGenerator functionality (response generation only)

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and API endpoints
- **Speed**: Medium (1-5 seconds per test)
- **Scope**: Multiple components working together
- **Coverage**: API endpoints with service layer integration

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows
- **Speed**: Slower (5+ seconds per test)
- **Scope**: Full application functionality
- **Coverage**: Real user scenarios across multiple services

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Test Type
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests only  
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/
```

### Run Specific Service Tests
```bash
# Test specific service
pytest tests/unit/services/test_chat_service.py

# Test specific function
pytest tests/unit/services/test_chat_service.py::TestChatService::test_process_chat_success
```

### Run with Coverage
```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

### Run with Verbose Output
```bash
pytest -v
```

## Test Configuration

### Fixtures (`conftest.py`)
The `conftest.py` file provides shared fixtures for all tests:

- **Service Fixtures**: Fresh instances of each service
- **Mock Fixtures**: Pre-configured mocks for common scenarios  
- **Data Fixtures**: Sample requests and test data
- **Error Scenarios**: Fixtures for testing error conditions

### Markers
Tests are marked with pytest markers for easy selection:

```bash
# Run only async tests
pytest -m asyncio

# Skip slow tests
pytest -m "not slow"
```

## Writing Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>_<scenario>`

### Test Structure (AAA Pattern)
```python
@pytest.mark.asyncio
async def test_feature_success(self, fixture):
    """Test description"""
    # Arrange
    service = ServiceClass()
    input_data = {...}
    
    # Act
    result = await service.method(input_data)
    
    # Assert
    assert result.status == "success"
    assert result.data == expected_data
```

### Mocking Guidelines
- Mock external dependencies (approaches, databases, APIs)
- Use `AsyncMock` for async methods
- Verify mock calls when testing interactions
- Use `patch` decorators for clean mocking

### Test Data
- Use fixtures for reusable test data
- Keep test data minimal but realistic
- Include edge cases (empty strings, large data, special characters)

## Best Practices

### SOLID Principles in Tests
Following the same SOLID principles used in the main code:

1. **Single Responsibility**: Each test tests one specific behavior
2. **Open/Closed**: Tests can be extended without modifying existing ones
3. **Liskov Substitution**: Mocks behave like real objects
4. **Interface Segregation**: Tests depend only on what they need
5. **Dependency Inversion**: Tests use mocks instead of concrete dependencies

### Test Coverage Goals
- **Unit Tests**: 90%+ coverage of service methods
- **Integration Tests**: Cover all API endpoints
- **E2E Tests**: Cover major user workflows

### Performance
- Unit tests should run in < 1 second each
- Integration tests should run in < 5 seconds each
- Use mocks to avoid external dependencies
- Parallelize tests when possible

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Tests
  run: |
    pytest tests/unit/ --cov=app
    pytest tests/integration/
    pytest tests/e2e/
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run tests before commit
pytest tests/unit/
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes the project root
2. **Async Test Failures**: Use `@pytest.mark.asyncio` decorator
3. **Mock Issues**: Verify patch paths match actual import paths
4. **Fixture Scope**: Use appropriate fixture scope for test isolation

### Debug Mode
```bash
# Run tests with debug output
pytest -s -vv

# Drop into debugger on failure
pytest --pdb
```

## Maintenance

### Adding New Tests
1. Follow the existing structure and naming conventions
2. Add appropriate fixtures to `conftest.py` if needed
3. Ensure tests are isolated and don't depend on each other
4. Update this README if adding new test categories

### Updating Tests
- Keep tests updated when modifying services
- Maintain backward compatibility in fixtures
- Update test data when schemas change
- Review and update mocks when dependencies change 