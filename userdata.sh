#!/bin/bash
yum install -y docker
systemctl enable docker
systemctl start docker
usermod -a -G docker ec2-user

# Install SSM agent (already on Amazon Linux 2, just enable it)
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Login to ECR and run container
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 593755927741.dkr.ecr.us-east-1.amazonaws.com
docker run -d -p 8501:8501 --name chatbot --restart always 593755927741.dkr.ecr.us-east-1.amazonaws.com/bedrock-chatbot:latest
