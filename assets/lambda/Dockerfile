FROM public.ecr.aws/lambda/python:3.13-x86_64

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

RUN dnf update -y && dnf install -y git libicu-devel gcc gcc-c++

# Copy requirements.txt
COPY requirements.txt .

# Install the specified packages
RUN uv pip install --system -r requirements.txt

# Lots of trouble with newer pyicus on Amazon Linux
RUN uv pip install --system "pyicu"

COPY . .

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda-handlers.apig_wsgi_handler" ]
