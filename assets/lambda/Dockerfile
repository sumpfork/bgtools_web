FROM public.ecr.aws/lambda/python:3.11.2024.05.14.09-x86_64

RUN yum update -y && yum install -y git libicu-devel gcc gcc-c++

# Copy requirements.txt
COPY requirements.txt .

RUN pip install pyicu

ARG CA_TOKEN
RUN if [[ -n "$CA_TOKEN" ]] ; then echo "setting CA_TOKEN"; pip config set global.index-url https://aws:$CA_TOKEN@pgorniak-572001094971.d.codeartifact.us-west-2.amazonaws.com/pypi/mypypi/simple/ ; fi

# Install the specified packages
RUN pip install -r requirements.txt --only-binary :all:

# Copy function code
COPY . .

COPY lambda-handlers.py .

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda-handlers.apig_wsgi_handler" ]
