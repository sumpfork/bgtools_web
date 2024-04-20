FROM public.ecr.aws/lambda/python:3.11-x86_64

RUN yum update -y && yum install -y git libicu-devel gcc gcc-c++

# Copy requirements.txt
COPY requirements.txt .

# Install the specified packages
RUN pip install -r requirements.txt --only-binary :all:

RUN pip install pyicu

# Copy function code
COPY . .

COPY lambda-handlers.py .

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda-handlers.apig_wsgi_handler" ]
