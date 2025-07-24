# In Vivo Study Scheduler Agent Requirements

## Functional Requirements

1. **Study Schedule Optimization**
   - Accept input of multiple study requests for a 30-day period
   - Each study request includes a number of animals required
   - Optimize the schedule to distribute studies evenly across the month
   - Ensure no day exceeds the maximum capacity of 1000 animals
   - Balance both the number of studies and number of animals per day

2. **Input Format**
   - Accept a list of study requests with the following information:
     - Study ID
     - Number of animals required
     - Preferred start date (optional)
     - Duration of study (days)
     - Priority level (optional)

3. **Output Format**
   - Return an optimized schedule showing:
     - Assigned start date for each study
     - Daily animal usage
     - Daily study count
     - Visualization of resource utilization across the month

4. **Constraints**
   - Maximum 1000 animals available per day
   - Studies must be scheduled within the 30-day period
   - Minimize deviation from average daily animal usage
   - Minimize deviation from average daily study count

## Technical Requirements

1. **AWS Infrastructure**
   - Amazon Bedrock with appropriate action groups
   - Lambda function using a custom container with OR-Tools
   - CloudFormation template for deployment

2. **Container Requirements**
   - Python environment with OR-Tools and other optimization libraries
   - Support for mathematical optimization models
   - Ability to handle complex scheduling constraints

3. **Integration**
   - Seamless integration with the existing HCLS Agents Toolkit
   - Consistent interface with other agents in the catalog
   - Proper error handling and validation

4. **Performance**
   - Solve optimization problems efficiently (within Lambda execution limits)
   - Handle up to 100 study requests in a single optimization run
