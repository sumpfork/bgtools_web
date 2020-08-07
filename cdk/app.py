#!/usr/bin/env python3

import subprocess
import os

from aws_cdk import (
    aws_lambda as lambda_,
    aws_lambda_python as lambda_python,
    aws_apigateway as apig,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    core,
)

app = core.App()


def rsync(fromd: str, tod: str):
    subprocess.check_call(
        [
            "rsync",
            "-a",
            "--delete",
            f"{os.path.abspath(fromd)}/",
            f"{os.path.abspath(tod)}/",
        ]
    )


class BGToolsStack(core.Stack):
    def __init__(self, app: core.App, id: str) -> None:
        super().__init__(app, id)

        self.lambda_dir = "assets/lambda"

        static_website_bucket = s3.Bucket(
            self,
            "Dominion Divider Generator Site",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,
        )

        s3_deployment.BucketDeployment(
            self,
            "Static Files Deployment",
            sources=[s3_deployment.Source.asset("./static")],
            destination_bucket=static_website_bucket,
            destination_key_prefix="static",
        )

        api = apig.RestApi(self, "bgtools-api")

        flask_app = lambda_python.PythonFunction(
            self,
            "DominionDividersFlaskApp",
            entry=self.lambda_dir,
            index="lambda-handlers.py",
            handler="flask_app",
            environment={"STATIC_WEB_URL": static_website_bucket.bucket_website_url},
            timeout=core.Duration.seconds(5),
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
        flask_endpoint = apig.LambdaIntegration(flask_app, proxy=True)
        api.root.add_proxy(default_integration=flask_endpoint)

        bar = lambda_.Function(
            self,
            "DominionDividersBar",
            code=lambda_.Code.from_asset(self.lambda_dir),
            handler="lambda-handlers.bar",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
        bar_endpoint = apig.LambdaIntegration(bar)
        api.root.add_resource("bar").add_proxy(default_integration=bar_endpoint)

        generate = lambda_.Function(
            self,
            "DominionDividersGenerate",
            code=lambda_.Code.from_asset(self.lambda_dir),
            handler="lambda-handlers.generate",
            timeout=core.Duration.seconds(300),
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
        generate_endpoint = apig.LambdaIntegration(generate)
        api.root.add_resource("generate").add_method("PUT", generate_endpoint)


BGToolsStack(app, "bgtools")
app.synth()
