# Contributing to Medical Device Management Agent

Thank you for your interest in contributing to this project! This document provides guidelines for contributing to the Medical Device Management Agent.

## Development Setup

1. **Prerequisites:**
   - Node.js 18+ and npm
   - Python 3.11+
   - Docker Desktop
   - AWS CLI configured

2. **Local Development:**
   ```bash
   # Install dependencies
   npm install
   pip install -r requirements.txt
   
   # Run locally
   streamlit run app.py
   ```

3. **Testing Deployment:**
   ```bash
   npx cdk bootstrap  # First time only
   npx cdk deploy
   ```

## Code Style

- **TypeScript**: Follow AWS CDK TypeScript conventions
- **Python**: Follow PEP 8 style guidelines
- **Documentation**: Update README.md for any new features

## Adding New Features

### New Agent Tools

1. Create tool in `tools/` directory
2. Add proper type hints and docstrings
3. Import in `agents/medical_coordinator.py`
4. Update system prompt if needed
5. Test locally before submitting

### UI Enhancements

1. Modify `app.py` for Streamlit changes
2. Ensure responsive design
3. Test with different screen sizes
4. Update documentation

### Infrastructure Changes

1. Modify CDK stacks in `cdk/stacks/`
2. Update IAM permissions as needed
3. Test deployment in clean environment
4. Document any new AWS services used

## Submission Guidelines

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** following the guidelines above
4. **Test thoroughly** both locally and in AWS
5. **Update documentation** including README.md
6. **Submit a pull request** with clear description

## Pull Request Requirements

- [ ] Code follows project conventions
- [ ] All tests pass locally
- [ ] Documentation updated
- [ ] CDK deployment tested
- [ ] No hardcoded credentials or sensitive data
- [ ] IAM permissions follow least privilege
- [ ] Clear commit messages

## Security Considerations

- Never commit AWS credentials or API keys
- Follow AWS security best practices
- Use IAM roles with minimal required permissions
- Validate all user inputs
- Keep dependencies updated

## Questions?

Feel free to open an issue for questions or clarifications before starting development.