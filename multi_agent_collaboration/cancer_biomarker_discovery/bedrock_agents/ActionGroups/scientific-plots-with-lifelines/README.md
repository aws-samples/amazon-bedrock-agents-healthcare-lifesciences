1. Change into function directory where the Dockerfile exists. 

 cd scientific-plots-with-lifelines

1. Create image with docker

 docker build -t lifelines-python3.12-v2 .

1. Create ECR Repo

aws ecr create-repository --repository-name lifelines-lambda-sample


1. Log into ECR

aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNTID.dkr.ecr.us-east-1.amazonaws.com


1. Tag the docker image 

docker tag lifelines-python3.12-v2:latest ACCOUNTID.dkr.ecr.us-east-1.amazonaws.com/lifelines-lambda-sample:latest 


1. Push image to ECR

docker push ACCOUNTID.dkr.ecr.us-east-1.amazonaws.com/lifelines-lambda-sample:latest 
