#!/usr/bin/env python3

import subprocess
import os

from aws_cdk import (
    aws_certificatemanager as acm,
    aws_lambda as lambda_,
    aws_lambda_python as lambda_python,
    aws_apigateway as apig,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    core,
)
from aws_cdk.aws_apigateway import DomainNameOptions

app = core.App()


class BGToolsStack(core.Stack):
    def __init__(self, app: core.App, id: str) -> None:
        super().__init__(app, id)

        self.lambda_dir = "assets/lambda"

        static_website_bucket = s3.Bucket(
            self,
            "Dominion Divider Generator Site",
            # website_index_document="index.html",
            # website_error_document="error.html",
            # public_read_access=True,
        )

        cf_static_dist = cloudfront.Distribution(
            self,
            "StaticCloudfrontDist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.S3Origin(static_website_bucket)
            ),
        )

        s3_deployment.BucketDeployment(
            self,
            "Static Files Deployment",
            sources=[s3_deployment.Source.asset("./static")],
            destination_bucket=static_website_bucket,
            destination_key_prefix="static",
        )

        flask_app = lambda_python.PythonFunction(
            self,
            "DominionDividersFlaskApp",
            entry=self.lambda_dir,
            index="lambda-handlers.py",
            handler="flask_app",
            environment={
                "STATIC_WEB_URL": f"https://{cf_static_dist.domain_name}",
                "FLASK_SECRET_KEY": "",  # fill in console once deployed
            },
            timeout=core.Duration.seconds(5),
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
        api = apig.LambdaRestApi(
            self,
            "bgtools-api",
            handler=flask_app,
            # domain_name=DomainNameOptions(
            #     domain_name="domdiv.bgtools.net",
            #     certificate=acm.Certificate.from_certificate_arn(
            #         self,
            #         "cert",
            #         "arn:aws:acm:us-west-2:572001094971:certificate/f0f173fd-5203-4066-ba19-b044c5de1004",
            #     ),
            # ),
        )
        cf_bgtools_dist = cloudfront.Distribution(
            self,
            "BGToolsCloudfrontDist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.HttpOrigin(
                    core.Fn.select(2, core.Fn.split("/", api.url)),
                    origin_path=core.Fn.join(
                        "", ["/", core.Fn.select(3, core.Fn.split("/", api.url))]
                    ),
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL
            ),
            domain_names=["domdiv.bgtools.net"],
            certificate=acm.Certificate.from_certificate_arn(
                self,
                "cert",
                "arn:aws:acm:us-east-1:572001094971:certificate/51cbd5c4-62a0-48eb-9459-963fad97fac1",
            ),
        )
        # flask_endpoint = apig.LambdaIntegration(flask_app)
        # api.root.add_proxy(default_integration=flask_endpoint)

        # api.root.add_resource("static").add_proxy(
        #     default_integration=apig.HttpIntegration(
        #         f"{static_website_bucket.bucket_website_url}/static/",
        #         proxy=True,
        #         http_method="GET",
        #     )
        # )
        # generate = lambda_.Function(
        #     self,
        #     "DominionDividersGenerate",
        #     code=lambda_.Code.from_asset(self.lambda_dir),
        #     handler="lambda-handlers.generate",
        #     timeout=core.Duration.seconds(300),
        #     runtime=lambda_.Runtime.PYTHON_3_7,
        # )
        # generate_endpoint = apig.LambdaIntegration(generate)
        # api.root.add_resource("generate").add_method("PUT", generate_endpoint)


BGToolsStack(app, "bgtools")
app.synth()
