# In Vivo Study Scheduler Agent Design

## Architecture Overview

The In Vivo Study Scheduler Agent is designed to optimize the scheduling of in vivo studies across a 30-day period, balancing resource utilization and adhering to capacity constraints. The architecture consists of the following components:

![Architecture Diagram](./images/architecture.png)

### Components

1. **Amazon Bedrock Agent**
   - Provides the conversational interface for users
   - Processes natural language requests and extracts study scheduling parameters
   - Invokes the appropriate action group based on user intent

2. **Action Groups**
   - **ScheduleOptimizer**: Main action group for optimizing study schedules
     - Function: `optimizeSchedule` - Takes study requests and returns optimized schedule

3. **Lambda Function with Custom Container**
   - Implements the optimization logic using OR-Tools
   - Processes the study requests and constraints
   - Returns the optimized schedule

4. **Container Image**
   - Based on Anaconda Python environment
   - Includes OR-Tools, PuLP, Pyomo, and other optimization libraries
   - Stored in Amazon ECR

## Optimization Approach

The scheduling optimization will use a constraint programming approach with the following objectives:

1. **Primary Objective**: Minimize the maximum deviation from average daily animal usage
2. **Secondary Objective**: Minimize the maximum deviation from average daily study count

### Constraints

1. Daily animal capacity limit (1000 animals)
2. All studies must be scheduled within the 30-day period
3. Studies with specific duration must be accommodated in consecutive days
4. Optional preferred start dates should be respected when possible

### Algorithm

The optimization will use OR-Tools' constraint solver with the following approach:

1. Define decision variables for each study's start date
2. Define auxiliary variables for daily resource usage
3. Set up constraints for capacity and scheduling requirements
4. Define the objective function to minimize deviations
5. Solve the optimization problem
6. Return the optimized schedule

## Data Flow

1. User submits study scheduling request via the Bedrock Agent
2. Agent extracts study parameters and invokes the ScheduleOptimizer action group
3. Lambda function processes the request and runs the optimization algorithm
4. Optimized schedule is returned to the user with visualizations and metrics

## Integration with Toolkit

The agent will be integrated with the existing HCLS Agents Toolkit through:

1. Consistent CloudFormation template structure
2. Shared container building workflow
3. Standard response format compatible with the React UI
