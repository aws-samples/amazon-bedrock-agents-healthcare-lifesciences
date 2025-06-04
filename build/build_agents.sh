#!/bin/bash

# Debug: Print current location and S3 bucket
echo "Current directory: $(pwd)"
echo "S3 Bucket: ${S3_BUCKET}"

# Process templates in build folder
# cd build || exit
pushd build || exit
echo "Processing build templates..."
template="codebuild.yaml"
echo "Found template file: ${template}"
template_name=$(basename "${template}" .yaml)
echo "Packaging template: ${template_name}"
aws cloudformation package \
  --template-file "${template}" \
  --s3-bucket "${S3_BUCKET}" \
  --output-template-file "../packaged_${template_name}.yaml"
# Copy to S3 immediately after packaging
aws s3 cp "../packaged_${template_name}.yaml" "s3://${S3_BUCKET}/packaged_${template_name}.yaml"  
popd

# for template in *.yaml; do
#   if [ -f "${template}" ]; then
#     echo "Found template file: ${template}"
#     template_name=$(basename "${template}" .yaml)
#     echo "Packaging template: ${template_name}"
#     aws cloudformation package \
#       --template-file "${template}" \
#       --s3-bucket "${S3_BUCKET}" \
#       --output-template-file "../packaged_${template_name}.yaml"
    
#     # Copy to S3 immediately after packaging
#     aws s3 cp "../packaged_${template_name}.yaml" "s3://${S3_BUCKET}/packaged_${template_name}.yaml"
#   fi
# done
# # cd ..
# popd

# Process Cancer biomarker discovery Subagent templates
# cd multi_agent_collaboration/cancer_biomarker_discovery/agents || exit
pushd multi_agent_collaboration/cancer_biomarker_discovery/agents || exit
echo "Processing agent templates..."
for agent_file in *.yaml; do
  if [ -f "${agent_file}" ]; then
    echo "Found agent file: ${agent_file}"
    agent_name=$(basename "${agent_file}" .yaml)
    echo "Packaging agent: ${agent_name}"
    aws cloudformation package \
      --template-file "${agent_file}" \
      --s3-bucket "${S3_BUCKET}" \
      --output-template-file "../packaged_${agent_name}.yaml"
    
    # Copy to S3 immediately after packaging
    aws s3 cp "../packaged_${agent_name}.yaml" "s3://${S3_BUCKET}/packaged_${agent_name}.yaml"
  fi
done
# cd ..
# cd ..
# cd ..
popd

# Process Cancer Biomarker discovery Supervisor agent template - note the quotes around directory name
# cd multi_agent_collaboration/cancer_biomarker_discovery/SupervisorAgent || exit
pushd multi_agent_collaboration/cancer_biomarker_discovery/SupervisorAgent || exit
echo "Processing supervisor agent template..."
if [ -f "supervisor_agent.yaml" ]; then
  echo "Packaging supervisor agent"
  aws cloudformation package \
    --template-file supervisor_agent.yaml \
    --s3-bucket "${S3_BUCKET}" \
    --output-template-file "../packaged_supervisor_agent.yaml"
  
  # Copy to S3 immediately after packaging
  aws s3 cp "../packaged_supervisor_agent.yaml" "s3://${S3_BUCKET}/packaged_supervisor_agent.yaml"
fi
# cd ..
# cd ..
# cd ..
popd

# Process agent build template
echo "Processing agent build template..."
if [ -f "agent_build.yaml" ]; then
  echo "Packaging agent build template"
  aws cloudformation package \
    --template-file agent_build.yaml \
    --s3-bucket "${S3_BUCKET}" \
    --output-template-file "packaged_agent_build.yaml"
  
  # Copy to S3
  aws s3 cp "packaged_agent_build.yaml" "s3://${S3_BUCKET}/packaged_agent_build.yaml"
fi

# Process agent catalog templates. NOTE: Uses a different S3 destination path!
# cd agents_catalog || exit
pushd agents_catalog || exit
echo "Processing agent templates..."
for agent_file in $(find . -type f -maxdepth 2 -name "*.yaml"); do
  if [ -f "${agent_file}" ]; then
    echo "Found agent file: ${agent_file}"
    agent_name=$(basename "${agent_file}" .yaml)
    echo "Packaging agent: ${agent_name}"
    aws cloudformation package \
      --template-file "${agent_file}" \
      --s3-bucket "${S3_BUCKET}" \
      --output-template-file "../packaged_${agent_name}.yaml"

    # Copy to S3 immediately after packaging
    aws s3 cp "../packaged_${agent_name}.yaml" "s3://${S3_BUCKET}/agents_catalog/packaged_${agent_name}.yaml"
    rm "../packaged_${agent_name}.yaml"
  fi
done
# cd ..
popd

# Process multi-agent catalog templates NOTE: Uses a different S3 destination path!
# cd multi_agent_collaboration || exit
pushd multi_agent_collaboration || exit
echo "Processing multi-agent templates..."
for agent_file in $(find . -type f -name "*.yaml"); do
  if [ -f "${agent_file}" ]; then
    echo "Found agent file: ${agent_file}"
    agent_name=$(basename "${agent_file}" .yaml)
    echo "Packaging agent: ${agent_name}"
    aws cloudformation package \
      --template-file "${agent_file}" \
      --s3-bucket "${S3_BUCKET}" \
      --output-template-file "../packaged_${agent_name}.yaml"

    # Copy to S3 immediately after packaging
    aws s3 cp "../packaged_${agent_name}.yaml" "s3://${S3_BUCKET}/agents_catalog/packaged_${agent_name}.yaml"
    rm "../packaged_${agent_name}.yaml"
  fi
done
# cd ..
popd

# Process additional artifacts. NOTE: Uses a different S3 destination path!
echo "Uploading additional artifacts"
aws s3 cp agents_catalog/10-SEC-10-K-agent/action-groups/SEC-10-K-search/docker/sec-10-k-docker.zip "s3://${S3_BUCKET}/agents_catalog/sec-10-k-docker.zip"
aws s3 cp agents_catalog/15-clinical-study-research-agent/lambdalayers/matplotlib.zip "s3://${S3_BUCKET}/agents_catalog/matplotlib.zip"


echo "All templates packaged and uploaded to S3"