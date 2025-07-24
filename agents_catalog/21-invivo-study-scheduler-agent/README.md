# In Vivo Study Scheduler Agent

This agent optimizes the scheduling of in vivo studies across a 30-day period, ensuring efficient resource utilization while respecting capacity constraints and study requirements. The agent uses advanced optimization algorithms to balance animal usage and study distribution across the month.

## Features

- **Intelligent Schedule Optimization**: Uses OR-Tools constraint programming to create optimal study schedules
- **Resource Constraint Management**: Ensures daily animal capacity limits are never exceeded (configurable, default 1000 animals/day)
- **Load Balancing**: Distributes studies and animal usage evenly across the month to avoid resource spikes
- **Flexible Study Parameters**: Supports study duration, preferred start dates, and priority levels
- **Constraint Satisfaction**: Handles complex scheduling constraints while optimizing for multiple objectives

## Architecture

The agent leverages a custom container-based Lambda function with optimization libraries:

- **Amazon Bedrock**: Provides conversational interface for study scheduling requests
- **Lambda Function with Custom Container**: Implements optimization logic using OR-Tools
- **Schedule Optimizer Action Group**: Processes study requests and returns optimized schedules
- **Container Image**: Includes OR-Tools, PuLP, Pyomo, and visualization libraries

## Optimization Approach

The scheduler uses a multi-objective optimization strategy:

1. **Primary Objective**: Minimize maximum deviation from average daily animal usage
2. **Secondary Objective**: Minimize maximum deviation from average daily study count

### Constraints

- Daily animal capacity limit (default: 1000 animals)
- All studies must fit within the 30-day scheduling period
- Studies with specific durations require consecutive days
- Optional preferred start dates are respected when feasible
- Priority levels influence scheduling preferences

## Deployment

The agent is deployed using AWS CloudFormation with all necessary resources:

- Amazon Bedrock with action groups
- Lambda function with custom container image
- Amazon ECR repository for container storage
- IAM roles and permissions
- CloudWatch logging

### Prerequisites

- AWS CLI configured with appropriate permissions
- Amazon Bedrock access enabled
- Docker installed for container building
- IAM permissions for ECR, Lambda, and Bedrock

### Deployment Steps

1. Create an S3 bucket for deployment artifacts (if needed):

```bash
aws s3 mb s3://YOUR_S3_BUCKET_NAME
```

2. Navigate to the agent directory:

```bash
cd agents_catalog/21-invivo-study-scheduler-agent
```

3. Upload container definition to S3

```bash
zip -jr container.zip action-groups/schedule-optimizer/container
aws s3 cp container.zip s3://YOUR_S3_BUCKET_NAME
```

3. Set environment variables and deploy:

```bash
export BUCKET_NAME="<YOUR_S3_BUCKET>"
export NAME="<STACK_NAME>"
export REGION="<AWS_REGION>"
export BEDROCK_AGENT_SERVICE_ROLE_ARN="<BEDROCK_SERVICE_ROLE_ARN>"

aws cloudformation package --template-file "invivo-study-scheduler-agent-cfn.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "packaged_invivo-study-scheduler-agent-cfn.yaml" \
  --region $REGION
aws cloudformation deploy --template-file "packaged_invivo-study-scheduler-agent-cfn.yaml" \
  --s3-bucket $BUCKET_NAME \
  --capabilities CAPABILITY_IAM \
  --stack-name $STACK_NAME \
  --region $REGION \
  --disable-rollback \
  --parameter-overrides \
    AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARN \
    S3CodeBucket=$S3CodeBucket \
    S3CodeKey="container.zip" \
    BuildContextPath="."
rm packaged_invivo-study-scheduler-agent-cfn.yaml
```

## Usage Examples

### Basic Study Scheduling

"I need to schedule 5 in vivo studies for the next 30 days. Study A needs 150 animals for 3 days, Study B needs 200 animals for 2 days, Study C needs 100 animals for 1 day, Study D needs 300 animals for 4 days, and Study E needs 80 animals for 2 days. Please optimize the schedule."

### Advanced Scheduling with Preferences

"Schedule these studies with preferences: Study A (150 animals, 3 days, prefer starting day 5), Study B (200 animals, 2 days, high priority), Study C (100 animals, 1 day), Study D (300 animals, 4 days, prefer starting day 10), Study E (80 animals, 2 days, low priority). Maximum capacity is 500 animals per day."

### Schedule Analysis

"Analyze the current study schedule and suggest improvements for better resource utilization across the month."

### Capacity Planning

"What's the optimal way to distribute 10 studies requiring between 50-300 animals each across a 30-day period with a daily limit of 800 animals?"

## Input Parameters

The agent accepts study requests with the following parameters:

- **Study ID**: Unique identifier for the study
- **Number of Animals**: Required animal count for the study
- **Duration**: Number of consecutive days needed (default: 1)
- **Preferred Start Date**: Optional preferred starting day (1-30)
- **Priority Level**: High, Medium, or Low (default: Medium)
- **Daily Capacity Limit**: Maximum animals available per day (default: 1000)

## Output Format

The agent provides comprehensive scheduling results:

- **Optimized Schedule**: Start date assignment for each study
- **Daily Resource Usage**: Animal count and study count per day
- **Utilization Metrics**: Average usage, peak usage, and distribution statistics
- **Visual Charts**: Resource utilization graphs and schedule timeline
- **Constraint Validation**: Confirmation that all constraints are satisfied

## Customization

You can customize the agent by:

1. **Modifying Optimization Parameters**: Adjust weights for different objectives in the container code
2. **Adding New Constraints**: Implement additional scheduling rules in the optimization algorithm
3. **Updating Capacity Limits**: Change default animal capacity or add equipment constraints
4. **Enhancing Visualizations**: Add new chart types or metrics in the output formatting
5. **Extending Input Parameters**: Support additional study metadata or requirements

## Technical Details

### Container Components

- **Python 3.9** runtime environment
- **OR-Tools** for constraint programming and optimization
- **Matplotlib/Plotly** for visualization generation
- **Pandas/NumPy** for data manipulation
- **AWS Lambda Powertools** for event handling

### Performance Characteristics

- Handles up to 100 study requests in a single optimization
- Typical solving time: 1-10 seconds for most scenarios
- Memory usage: 512MB-1GB depending on problem complexity
- Timeout: 15 minutes maximum (Lambda limit)

### Error Handling

- Input validation for study parameters
- Infeasibility detection and reporting
- Graceful degradation for complex scenarios
- Detailed error messages for troubleshooting

## Integration

This agent integrates seamlessly with the HCLS Agents Toolkit and can be combined with other agents for comprehensive research workflow management. It's particularly useful when paired with:

- **Clinical Trial Protocol Generator Agent**: For planning study timelines
- **Statistical Analysis Agent**: For power calculations and sample size determination
- **Clinical Evidence Researcher Agent**: For background research on study designs

## Support and Troubleshooting

Common issues and solutions:

- **Infeasible Schedules**: Reduce study requirements or extend the scheduling period
- **Suboptimal Results**: Adjust priority levels or preferred start dates
- **Performance Issues**: Reduce the number of studies or simplify constraints
- **Container Errors**: Check CloudWatch logs for detailed error information

For additional support, refer to the CloudWatch logs and the agent's test scripts in the repository.
