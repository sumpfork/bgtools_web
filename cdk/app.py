#!/usr/bin/env python3

import datetime as dt
import json
import os
import requests

from jinja2 import Environment, FileSystemLoader, select_autoescape

from aws_cdk import (
    aws_certificatemanager as acm,
    aws_cloudwatch,
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

        with open("config.json") as f:
            self.config = json.load(f)
        assert (
            "SECRET_KEY" in self.config
        ), "Need random SECRET_KEY specified in config.json"
        assert (
            "CERTIFICATE_ARN" in self.config
        ), "Need CERTIFICATE_ARN specified in config.json"

        self.lambda_dir = "assets/lambda"
        os.makedirs(
            os.path.join(self.lambda_dir, "templates", "generated"), exist_ok=True
        )

        r = requests.get("https://api.github.com/repos/sumpfork/dominiontabs/releases")
        changelog = r.json()
        changelog = [
            {
                "url": ch["html_url"],
                "date": dt.datetime.strptime(
                    ch["published_at"][:10], "%Y-%m-%d"
                ).date(),
                "name": ch["name"],
                "tag": ch["tag_name"],
                "description": ch["body"],
            }
            for ch in changelog
        ]

        env = Environment(
            loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html"])
        )
        t = env.get_template("changelog.html.j2")
        with open(
            os.path.join(self.lambda_dir, "templates", "generated", "changelog.html"),
            "w",
        ) as f:
            f.write(t.render(changelog=changelog))

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
            handler="apig_wsgi_handler",
            environment={
                "STATIC_WEB_URL": f"https://{cf_static_dist.domain_name}",
                "FLASK_SECRET_KEY": self.config["SECRET_KEY"],
                "GA_CONFIG": self.config.get("GA_CONFIG", ""),
            },
            timeout=core.Duration.seconds(60),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_8,
        )
        api = apig.LambdaRestApi(
            self,
            "bgtools-api",
            handler=flask_app,
            binary_media_types=["*/*"],
            minimum_compression_size=10e4,
            deploy_options={
                "method_options": {
                    "/*/*": apig.MethodDeploymentOptions(
                        throttling_rate_limit=10, throttling_burst_limit=20
                    )
                }
            },
        )
        cloudfront.Distribution(
            self,
            "BGToolsCloudfrontDist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.HttpOrigin(
                    core.Fn.select(2, core.Fn.split("/", api.url)),
                    origin_path=core.Fn.join(
                        "", ["/", core.Fn.select(3, core.Fn.split("/", api.url))]
                    ),
                ),
                origin_request_policy=cloudfront.OriginRequestPolicy(
                    self,
                    "OriginRequestPolicy",
                    cookie_behavior=cloudfront.OriginRequestCookieBehavior.all(),
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            ),
            domain_names=["domdiv.bgtools.net"],
            certificate=acm.Certificate.from_certificate_arn(
                self,
                "cert",
                self.config["CERTIFICATE_ARN"],
            ),
        )

        dashboard = aws_cloudwatch.Dashboard(
            self,
            f"bgtools-dashboard",
            dashboard_name=f"bgtools-prod",
            start="-P1D",
            period_override=aws_cloudwatch.PeriodOverride.INHERIT,
        )
        dashboard.add_widgets(
            aws_cloudwatch.GraphWidget(
                title="API Gateway Counts",
                width=6,
                height=6,
                left=[
                    aws_cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="5XXError",
                        dimensions={
                            "ApiName": "bgtools-api",
                            "Stage": api.deployment_stage.stage_name,
                        },
                        period=core.Duration.minutes(amount=30),
                        statistic="Sum",
                        color="#d62728",
                    ),
                    aws_cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="4XXError",
                        dimensions={
                            "ApiName": "bgtools-api",
                            "Stage": api.deployment_stage.stage_name,
                        },
                        period=core.Duration.minutes(amount=30),
                        statistic="Sum",
                        color="#8c564b",
                    ),
                    aws_cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Count",
                        dimensions={
                            "ApiName": "bgtools-api",
                            "Stage": api.deployment_stage.stage_name,
                        },
                        period=core.Duration.minutes(amount=30),
                        statistic="Sum",
                        color="#2ca02c",
                    ),
                ],
            ),
            aws_cloudwatch.GraphWidget(
                title="API Gateway Latencies",
                width=6,
                height=6,
                left=[
                    aws_cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Latency",
                        dimensions={
                            "ApiName": "bgtools-api",
                            "Stage": api.deployment_stage.stage_name,
                        },
                        period=core.Duration.minutes(amount=30),
                        statistic="Average",
                    ),
                    aws_cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="IntegrationLatency",
                        dimensions={
                            "ApiName": "bgtools-api",
                            "Stage": api.deployment_stage.stage_name,
                        },
                        period=core.Duration.minutes(amount=30),
                        statistic="Average",
                    ),
                ],
            ),
        )


BGToolsStack(app, "bgtools")
app.synth()
