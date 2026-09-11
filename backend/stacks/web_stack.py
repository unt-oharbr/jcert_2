"""Static hosting for the Axiom frontend: a private S3 bucket behind CloudFront.

Deploys the built `frontend/dist` on every `cdk deploy` and invalidates the
whole CloudFront cache each time — simpler and more robust for a low-traffic
family app than a two-tier cache-control scheme, at the cost of a full
invalidation per deploy (well within the free monthly allowance).
"""

from __future__ import annotations

from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from constructs import Construct


class AxiomWebStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.site_bucket = s3.Bucket(
            self,
            "AxiomSiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.distribution = cloudfront.Distribution(
            self,
            "AxiomDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            # It's a single-page app: unknown paths (a refresh on a client-side
            # route) should still resolve to index.html, not a CloudFront 404.
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
        )

        s3_deployment.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3_deployment.Source.asset("../frontend/dist")],
            destination_bucket=self.site_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )
