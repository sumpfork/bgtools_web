#!/usr/bin/env python3

import datetime as dt
import os
import shutil
import time

import aws_cdk
import cdk_monitoring_constructs
import requests
import yaml
from aws_cdk import (
    aws_apigateway as apig,
)
from aws_cdk import (
    aws_certificatemanager as acm,
)
from aws_cdk import (
    aws_cloudfront as cloudfront,
)
from aws_cdk import (
    aws_cloudfront_origins as cloudfront_origins,
)
from aws_cdk import (
    aws_iam,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_s3_deployment as s3_deployment,
)
from jinja2 import Environment, FileSystemLoader, select_autoescape

invalidation_code = """
import os
import boto3

def invalidate_cloudfront_distribution(_, _2):
   client = boto3.client('cloudfront')

   response = client.create_invalidation(
       DistributionId=os.environ['DISTRIBUTION_ID'],
       InvalidationBatch={{
           'Paths': {{
               'Quantity': 1,
               'Items': ['/*']
           }},
           'CallerReference': "{t}"
       }}
   )

""".format(t=time.time())

app = aws_cdk.App()


class BGToolsStack(aws_cdk.Stack):
    def __init__(self, scope, id_, **kwargs):
        with open("config.yaml") as f:
            self.config = yaml.safe_load(f)

        # protect production stacks from accidental deletion
        kwargs["termination_protection"] = self.config.get("TERMINATION_PROTECTION")

        assert (
            "SECRET_KEY" in self.config
        ), "Need random SECRET_KEY specified in config.json"
        assert (
            "CERTIFICATE_ARN" in self.config
        ), "Need CERTIFICATE_ARN specified in config.json"

        self.stage = self.config["STAGE"]
        self.stackname = f"{id_}-{self.stage}"
        self.domain = self.config["DOMAIN"]

        super().__init__(scope, self.stackname, **kwargs)

        aws_cdk.Tags.of(self).add("id", id_)
        aws_cdk.Tags.of(self).add("stackname", self.stackname)

        monitoring_facade = cdk_monitoring_constructs.MonitoringFacade(
            self,
            "BGToolsMonitoringFacade",
            dashboard_factory=cdk_monitoring_constructs.DefaultDashboardFactory(
                self,
                "DashboardFactory",
                dashboard_name_prefix=f"{self.stackname}-dashboard",
            ),
        )

        self.lambda_dir = "assets/lambda"
        os.makedirs(
            os.path.join(self.lambda_dir, "templates", "generated"), exist_ok=True
        )

        local_fonts = self.config.get(
            "FONT_DIR",
        )
        if local_fonts:
            print(f"Copying local fonts in {local_fonts} to lambda directory")
            shutil.copytree(
                local_fonts,
                os.path.join(self.lambda_dir, "local_fonts"),
                dirs_exist_ok=True,
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
        generated_template_path = os.path.join(
            self.lambda_dir, "templates", "generated"
        )
        shutil.rmtree(generated_template_path)
        os.mkdir(generated_template_path)

        with open(
            os.path.join(generated_template_path, "changelog.html"),
            "w",
        ) as f:
            f.write(t.render(changelog=changelog))

        static_website_bucket = s3.Bucket(
            self,
            "Dominion Divider Generator Site",
        )
        monitoring_facade.monitor_s3_bucket(bucket=static_website_bucket)

        cf_static_dist = cloudfront.Distribution(
            self,
            "StaticCloudfrontDist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.S3Origin(static_website_bucket)
            ),
        )
        monitoring_facade.monitor_cloud_front_distribution(distribution=cf_static_dist)

        s3_deployment.BucketDeployment(
            self,
            "Static Files Deployment",
            sources=[s3_deployment.Source.asset("./static")],
            destination_bucket=static_website_bucket,
            destination_key_prefix="static",
            distribution=cf_static_dist,
            distribution_paths=["/*"],
        )

        ca_token = self.config.get("CA_TOKEN")

        flask_app = lambda_.DockerImageFunction(
            self,
            "DominionDividersDockerFlaskApp",
            code=lambda_.DockerImageCode.from_image_asset(
                "assets/lambda",
                build_args={"CA_TOKEN": ca_token} if ca_token else None,
            ),
            environment={
                "STATIC_WEB_URL": f"https://{cf_static_dist.domain_name}",
                "FLASK_SECRET_KEY": self.config["SECRET_KEY"],
                "GA_CONFIG": self.config.get("GA_CONFIG", ""),
                "LOG_LEVEL": self.config.get("LOG_LEVEL", "INFO"),
                "FONT_DIR": self.config.get("FONT_DIR", ""),
            },
            timeout=aws_cdk.Duration.seconds(60),
            memory_size=self.config.get("LAMBDA_MEMORY_SIZE", 1024),
        )
        monitoring_facade.monitor_lambda_function(lambda_function=flask_app)

        api = apig.LambdaRestApi(
            self,
            "bgtools-api",
            handler=flask_app,
            binary_media_types=["*/*"],
            min_compression_size=aws_cdk.Size.bytes(10e4),
            deploy_options={
                "method_options": {
                    "/*/*": apig.MethodDeploymentOptions(
                        throttling_rate_limit=10, throttling_burst_limit=20
                    )
                },
                "stage_name": self.stage,
            },
        )
        monitoring_facade.monitor_api_gateway(api=api)

        cloudfront_distribution = cloudfront.Distribution(
            self,
            "BGToolsCloudfrontDist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.HttpOrigin(
                    aws_cdk.Fn.select(2, aws_cdk.Fn.split("/", api.url)),
                    origin_path=aws_cdk.Fn.join(
                        "", ["/", aws_cdk.Fn.select(3, aws_cdk.Fn.split("/", api.url))]
                    ),
                ),
                origin_request_policy=cloudfront.OriginRequestPolicy(
                    self,
                    f"OriginRequestPolicy-{self.stackname}",
                    cookie_behavior=cloudfront.OriginRequestCookieBehavior.all(),
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            ),
            domain_names=[self.domain],
            certificate=acm.Certificate.from_certificate_arn(
                self,
                "cert",
                self.config["CERTIFICATE_ARN"],
            ),
        )
        monitoring_facade.monitor_cloud_front_distribution(
            distribution=cloudfront_distribution
        )
        invalidation_trigger = aws_cdk.triggers.TriggerFunction(
            self,
            "InvalidationTrigger",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.invalidate_cloudfront_distribution",
            code=lambda_.InlineCode(invalidation_code),
            environment={"DISTRIBUTION_ID": cloudfront_distribution.distribution_id},
        )
        invalidation_trigger.execute_after(cloudfront_distribution)
        invalidation_trigger.role.add_to_policy(
            aws_iam.PolicyStatement(
                resources=[
                    self.format_arn(
                        service="cloudfront",
                        resource="distribution",
                        region="",
                        resource_name=cloudfront_distribution.distribution_id,
                    ),
                ],
                actions=[
                    "cloudfront:CreateInvalidation",
                ],
            )
        )


BGToolsStack(
    app,
    "bgtools",
    env={
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    },
)
app.synth()
