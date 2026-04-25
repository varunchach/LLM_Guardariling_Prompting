#!/bin/bash
yum update -y
yum install -y docker
service docker start
usermod -a -G docker ec2-user
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 593755927741.dkr.ecr.us-east-1.amazonaws.com
docker run -d -p 8501:8501 --name chatbot --restart always 593755927741.dkr.ecr.us-east-1.amazonaws.com/bedrock-chatbot:latest
