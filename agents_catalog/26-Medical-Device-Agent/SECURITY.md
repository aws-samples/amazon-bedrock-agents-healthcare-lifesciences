# Security Configuration

## Authentication Setup

This application uses Basic Authentication to protect access. Follow these steps to configure secure credentials:

### 1. Environment Variables

Create a `.env` file (never commit this to version control):

```bash
ENABLE_AUTHENTICATION=true
AUTH_TYPE=basic
BASIC_AUTH_USERNAME=your_secure_username
BASIC_AUTH_PASSWORD=your_secure_password
AWS_DEFAULT_REGION=us-east-1
```

### 2. Password Requirements

- Use a strong, unique password
- Minimum 12 characters recommended
- Include uppercase, lowercase, numbers, and symbols
- Never use default or predictable passwords

### 3. Deployment Security

**AWS Deployment:**
- Credentials are automatically configured during CDK deployment
- Default credentials are set to `admin`/`password123` - **CHANGE THESE IMMEDIATELY**
- Update credentials in CDK stack environment variables

**Local Development:**
- Set environment variables in `.env` file
- Use different credentials than production
- Never commit `.env` file to version control

### 4. Security Best Practices

- Rotate passwords regularly
- Use environment-specific credentials
- Monitor access logs
- Consider implementing IP restrictions for production
- Use HTTPS in production environments

### 5. Reporting Security Issues

If you discover a security vulnerability, please report it responsibly by contacting the development team directly.