# Troubleshooting

This document explains common issues and solutions for the SiLA2 Lab Automation Agent.

## Common Issues

### Deployment Related

#### CloudFormation Stack Creation Fails

**Symptoms**: Error occurs during stack creation

**Solutions**:
- Check IAM permissions
- Check resource limits
- Review error messages

### Connection Related

#### gRPC Connection Error

**Symptoms**: gRPC connection to Bridge Server fails

**Solutions**:
- Check security group settings
- Check ECS task status
- Check CloudWatch Logs for errors

### AgentCore Related

#### Agent Not Responding

**Symptoms**: No response from Agent

**Solutions**:
- Check AgentCore status
- Check Lambda function logs
- Check timeout settings

## How to Check Logs

### CloudWatch Logs

### ECS Task Logs

### Lambda Function Logs

## Support

If the issue persists, please create a GitHub Issue.
