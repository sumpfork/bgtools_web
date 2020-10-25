import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="cdk",
    version="0.0.1",

    description="BGTools CDK App",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="Peter Gorniak",

    package_dir={"": "cdk"},
    packages=setuptools.find_packages(where="cdk"),

    install_requires=[
        "aws-cdk.core",
        "aws-cdk.aws_cloudfront",
        "aws-cdk.aws_cloudfront_origins",
        "aws-cdk.aws_lambda",
        "aws-cdk.aws_lambda_python",
        "aws-cdk.aws_apigateway",
        "aws-cdk.aws_s3",
        "aws-cdk.aws_s3_deployment"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
