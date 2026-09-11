"""Core Axiom backend: auth, data, and the API.

Deliberately one stack for Phase 0 — Cognito, DynamoDB, and the HTTP API
are wired together here since this is a single-family app with no need yet
for the stack boundaries a multi-team system would want. The AI-generation
pipeline (Bedrock, SES, EventBridge) is a later milestone, not this one.
"""

from __future__ import annotations

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_authorizers as apigwv2_authorizers
from aws_cdk import aws_apigatewayv2_integrations as apigwv2_integrations
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from constructs import Construct

# (url path, HTTP method, handler directory under lambdas/)
# No /review/* routes: Coordinate Geometry of the Line's content is served
# by a validated live generator (axiom/question_generators.py), not
# AI-generated text needing a review-and-approve pipeline, so there's
# nothing for Bedrock/SES to do in Phase 0 — see the plan's Milestone 8 note.
_ROUTES: list[tuple[str, str, str]] = [
    ("/session/next-question", "POST", "next_question"),
    ("/session/answer", "POST", "answer"),
    ("/diagnostic/{prerequisiteNodeId}", "GET", "diagnostic"),
    ("/questions/{questionId}/flag", "POST", "flag"),
    ("/progress", "GET", "progress"),
    ("/profile", "GET", "profile"),
    ("/profile", "PUT", "profile"),
]


class AxiomBackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool, self.user_pool_client = self._build_user_pool()
        self.tables = self._build_tables()
        self.shared_layer = lambda_.LayerVersion(
            self,
            "AxiomSharedLayer",
            code=lambda_.Code.from_asset("layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared axiom/ business-logic package used by every handler",
        )
        self.api = self._build_api()

    def _build_user_pool(self) -> tuple[cognito.UserPool, cognito.UserPoolClient]:
        user_pool = cognito.UserPool(
            self,
            "AxiomUserPool",
            # No public sign-up: her account is parent-seeded via
            # scripts/seed_user.py, not a self-serve form.
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True, username=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=6,
                require_lowercase=False,
                require_uppercase=False,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN,
        )
        client = user_pool.add_client(
            "AxiomWebClient",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
        )
        return user_pool, client

    def _build_tables(self) -> dict[str, dynamodb.Table]:
        def make_table(
            name: str, partition_key: str, sort_key: str | None = None, *, ttl_attribute: str | None = None
        ) -> dynamodb.Table:
            return dynamodb.Table(
                self,
                name,
                table_name=f"Axiom{name}",
                partition_key=dynamodb.Attribute(name=partition_key, type=dynamodb.AttributeType.STRING),
                sort_key=(
                    dynamodb.Attribute(name=sort_key, type=dynamodb.AttributeType.STRING) if sort_key else None
                ),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                removal_policy=RemovalPolicy.RETAIN,
                time_to_live_attribute=ttl_attribute,
            )

        return {
            "users": make_table("Users", "userId"),
            # Rows here are individual generated question *instances* written
            # at serve-time (see axiom/question_generators.py), not a
            # pre-seeded bank — TTL cleans them up once answered/abandoned.
            "questions": make_table("Questions", "questionId", ttl_attribute="ttl"),
            "attempts": make_table("Attempts", "userId", "timestamp"),
            "progress": make_table("ProgressState", "userId", "topicId"),
            "streaks": make_table("StreakState", "userId"),
            "flags": make_table("Flags", "questionId", "userId"),
        }

    def _table_env(self) -> dict[str, str]:
        return {
            "USERS_TABLE": self.tables["users"].table_name,
            "QUESTIONS_TABLE": self.tables["questions"].table_name,
            "ATTEMPTS_TABLE": self.tables["attempts"].table_name,
            "PROGRESS_TABLE": self.tables["progress"].table_name,
            "STREAKS_TABLE": self.tables["streaks"].table_name,
            "FLAGS_TABLE": self.tables["flags"].table_name,
        }

    def _build_function(self, handler_dir: str) -> lambda_.Function:
        construct_id = "".join(part.title() for part in handler_dir.split("_")) + "Fn"
        fn = lambda_.Function(
            self,
            construct_id,
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(f"lambdas/{handler_dir}"),
            layers=[self.shared_layer],
            timeout=Duration.seconds(10),
            environment=self._table_env(),
        )
        for table in self.tables.values():
            table.grant_read_write_data(fn)
        return fn

    def _build_api(self) -> apigwv2.HttpApi:
        api = apigwv2.HttpApi(
            self,
            "AxiomHttpApi",
            api_name="axiom-api",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["http://localhost:5173", "https://d1j5g1iwdlymr9.cloudfront.net"],
                allow_methods=[apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST, apigwv2.CorsHttpMethod.PUT],
                allow_headers=["Authorization", "Content-Type"],
            ),
        )

        authorizer = apigwv2_authorizers.HttpJwtAuthorizer(
            "AxiomJwtAuthorizer",
            jwt_issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}",
            jwt_audience=[self.user_pool_client.user_pool_client_id],
        )

        functions = {handler_dir: self._build_function(handler_dir) for handler_dir in {r[2] for r in _ROUTES}}

        for path, method, handler_dir in _ROUTES:
            integration_id = f"{handler_dir}-{method}-{path}".replace("/", "-").replace("{", "").replace("}", "")
            api.add_routes(
                path=path,
                methods=[apigwv2.HttpMethod[method]],
                integration=apigwv2_integrations.HttpLambdaIntegration(integration_id, functions[handler_dir]),
                authorizer=authorizer,
            )

        return api
