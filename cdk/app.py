#!/usr/bin/env python3

import datetime as dt
import os
import requests

from jinja2 import Environment, FileSystemLoader, select_autoescape

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
                "FLASK_SECRET_KEY": "",  # fill in console once deployed
            },
            timeout=core.Duration.seconds(60),
            memory_size=512,
            runtime=lambda_.Runtime.PYTHON_3_7,
        )
        api = apig.LambdaRestApi(
            self, "bgtools-api", handler=flask_app, binary_media_types=["*/*"]
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
                "arn:aws:acm:us-east-1:572001094971:certificate/51cbd5c4-62a0-48eb-9459-963fad97fac1",
            ),
        )


BGToolsStack(app, "bgtools")
app.synth()
