# Requirements for Single Cell QC Analysis Agent

## Purpose
Create an Amazon Bedrock agent that can analyze and validate quality control metrics for single cell gene expression assays by comparing web summary files against technical interpretation guidelines.

## Functional Requirements

1. **Web Summary Analysis**
   - Retrieve and parse web summary files (HTML) from S3
   - Extract key QC metrics and visualizations from the summary file
   - Present the metrics in a structured format

2. **Technical Validation**
   - Compare extracted metrics against technical interpretation guidelines
   - Identify any anomalies or quality issues based on standard QC measures
   - Provide validation results with explanations

3. **User Interaction**
   - Accept input parameters for web summary file location and technical document location
   - Return comprehensive analysis results with clear pass/fail indicators
   - Highlight specific areas of concern when quality issues are detected

## Technical Requirements

1. **AWS Integration**
   - Use AWS Lambda for agent action groups
   - Retrieve files from Amazon S3
   - Use Amazon Bedrock for document analysis and interpretation

2. **Performance**
   - Complete analysis within reasonable timeframe (< 30 seconds)
   - Handle large web summary files efficiently

3. **Security**
   - Follow least privilege principle for IAM roles
   - Ensure secure handling of potentially sensitive research data

## Constraints

1. Files are assumed to be available in Amazon S3
2. Web summary files follow the standard 10x Genomics Cell Ranger format
3. Technical interpretation documents are in PDF format
