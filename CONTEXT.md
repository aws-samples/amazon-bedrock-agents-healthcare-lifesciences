# CONTEXT.md

This file provides guidance to coding agents such as Amazon Q Developer or Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the AWS Healthcare and Life Sciences Agents Toolkit - a collection of specialized Amazon Bedrock agents for drug research, clinical trials, and commercialization workflows. The repository contains three main components:

* **agents_catalog/**: Library of 18+ specialized agents (biomarker analysis, clinical research, pathology, etc.)
* **multi_agent_collaboration/**: Framework for coordinating multiple agents on complex workflows
* **ui/**: Next.js React application providing a web interface to interact with deployed agents

## Architecture

### Agent Structure

Each agent follows a consistent pattern:

* CloudFormation template (`.yaml`) for infrastructure deployment
* Action groups in `/action-groups/` directories containing Lambda function implementations  
* README with deployment instructions and usage examples
* Optional Jupyter notebooks (`.ipynb`) for interactive development

## AWS Deployment

```bash
# Deploy main infrastructure stack
aws cloudformation deploy --template-file Infra_cfn.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name hcls-agents-toolkit \
  --parameter-overrides \
    RedshiftPassword="YourPassword123" \
    ReactAppAllowedCidr="192.0.2.0/24" \
    TavilyApiKey="your-tavily-key" \
    USPTOApiKey="your-uspto-key"

# Individual agent deployment
aws cloudformation deploy --template-file agents_catalog/[agent-name]/[agent-name]-cfn.yaml \
  --capabilities CAPABILITY_IAM \
  --stack-name [agent-stack-name]
```

## New agent development

### Development guidance

Follow this guidance when developing new agents for this toolkit:

* Use the agent defined in `agents_catalog/10-SEC-10-K-agent` as an example of best practices when creating a new agent.

* Ensure you are working within a git repo by running `git status`. If a git repo is not configured yet, create one by running `git init`.

* When creating a new agent, first create a new subfolder under `agents_catalog`. This folder name should follow the same pattern as the existing subfolders: `<two-digit index>-<agent name>`. For example, if the latest subfolder is named, "43-my-last-agent", the new agent should begin with "44", followed by a dash, followed by the agent name, like "44-my-new-agent". This agent folder should contain all of the information necessary to define the new agent.

* The agent folder must contain a README.md file. This README should consisely describe the agent and the use case it solves. Update and extend this README.md file with additional information about the project as development progresses, and commit changes to this file and the other planning files below as they are updated.

* Work with the user to implement the new agent step by step, first by working out the requirements, then the design/architecture including AWS infrastructure components, then the list of tasks needed to create the agent. Generally, the user will ask you to create two types of files:

  * CloudFormation templates written in yaml format.
  * Lambda functions written in Python and supporting data.

* Capture the agent design in additional planning files in the agent subfolder:

  * requirements.md: Defines the requirements for this project
  * design.md: Defines the design and architecture for this project
  * tasks.md: Lists the discrete tasks that need to be executed in order to successfully implement the project. Each task has a check box [ ] that is checked off when the task has been successfully completed. A git commit should be performed after any task is successfully completed.

  Once all planning steps are completed and documented, and the user is ready to proceed, begin implementing the tasks one at a time until the project is completed.

### CloudFormation Templates

* CloudFormation templates that define a Bedrock Agent should have at least three parameters:
  * AgentAliasName - Optional alias name. Defaults to "Latest"
  * BedrockModelId - Optional Bedrock foundation model id. Defaults to "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
  * AgentIAMRoleArn - Optional Bedrock Agent execution role. Defaults to ""

### Lambda Action Groups

Use Python 3.12 as the runtime for all lambda functions. Lambda code should have the standard handler structure:

```python
def lambda_handler(event, context):
    parameters = event.get('parameters', [])
    # Extract and validate parameters
    # Execute business logic
    return {
        'response': {
            'actionGroup': event['actionGroup'],
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': result_text
                    }
                }
            }
        }
    }
```

### Docker Containers

Use the `Image` Lambda package type for complex action groups (e.g., semantic search, image analysis). You can create new container images and upload them to ECR as part of the agent CloudFormation template by including the container building workflow as a nested stack. Here is an example from `agents_catalog/10-SEC-10-K-agent/sec-10-K-agent-cfn.yaml`:

```yaml
SEC10KSearchContainer:
Type: "AWS::CloudFormation::Stack"
Properties:
    TemplateURL: ../../build/container.yaml
    Parameters:
    S3CodeBucket:
        "Fn::If":
        - AgentS3BucketCondition
        - !Ref S3CodeBucket
        - "{{resolve:ssm:/s3/agent_build/name:1}}"
    S3CodeKey:
        Ref: S3CodeKey
    BuildContextPath: !Ref BuildContextPath
    ContainerName:
        Ref: ContainerName
    WaitForCodeBuild: "Y"
```

This example references the existing `container.yaml` template located at `build/container.yaml`. Use this template for all new containers. Do not define your own.

### Security

* Never commit API keys or sensitive credentials
* Use CloudFormation parameters with NoEcho for secrets
* Implement least-privilege IAM policies
* This is demonstration code - not for clinical production use
