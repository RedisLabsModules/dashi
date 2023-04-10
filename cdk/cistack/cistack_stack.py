from aws_cdk import Stack, Duration
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_logs as logs
from aws_cdk import aws_rds as rds
from aws_cdk import aws_route53 as route53
from aws_cdk import (
    aws_route53_targets,
    aws_secretsmanager,
    RemovalPolicy,
)
from constructs import Construct
from os import getenv

class DashiStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC with two public subnets
        vpc = ec2.Vpc(
            self,
            "DashiVPC",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="isolated",
                    cidr_mask=24,
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                ),
            ],
        )
        dashi_secret_circleci = aws_secretsmanager.Secret.from_secret_name_v2(
            self, "DashiCircleCiToken", "dashi_circle_ci_token"
        )
        dashi_secret_gh = aws_secretsmanager.Secret.from_secret_name_v2(
            self, "DashiGhToken", "dashi-gh-token"
        )

        rds_secret = aws_secretsmanager.Secret(
            self,
            "DashiRdsSecret",
            description="Dashi RDS secret",
            secret_name="dashi-rds-secret",
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "postgres"}',
                password_length=30,
                exclude_punctuation=True,
                generate_string_key="password",
            ),
        )

        # Create an instance of Amazon RDS PostgreSQL
        rds_instance = rds.DatabaseInstance(
            self,
            "DashiRdsInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_12
            ),
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
            ),
            database_name="dashi",
            credentials=rds.Credentials.from_secret(rds_secret),
            publicly_accessible=False,
        )

        # Use the existing ACM certificate for the load balancer's domain name
        certificate = acm.Certificate.from_certificate_arn(
            self,
            "DashiACMCert",
            "arn:aws:acm:eu-west-1:513600691417:certificate/f32eb2d2-b316-44c8-81d6-d8770547c456",
        )

        # Create a load balancer to handle incoming HTTPS traffic
        lb = elbv2.ApplicationLoadBalancer(
            self,
            "DashiLoadBalancer",
            vpc=vpc,
            internet_facing=True,
        )

        # Create a listener for HTTPS traffic on port 443 using the ACM certificate
        https_listener = lb.add_listener(
            "HttpsListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[
                elbv2.ListenerCertificate.from_certificate_manager(certificate)
            ],
        )

        # Create a Route53 record for the Dashi service
        route53.ARecord(
            self,
            "DashiRecord",
            zone=route53.HostedZone.from_lookup(
                self, "DashiZone", domain_name="cto.redislabs.com"
            ),
            record_name="dashi",
            target=route53.RecordTarget.from_alias(
                aws_route53_targets.LoadBalancerTarget(lb)
            ),
        )

        # Create a dedicated container registry
        dashi_repository = ecr.Repository(
            self, "DashiRepository", repository_name="dashi-repository"
        )
        dashi_repository.add_lifecycle_rule(
            max_image_count=20, description="Last 20 images"
        )
        dashi_repository.apply_removal_policy(RemovalPolicy.DESTROY)

        image_tag = getenv('GITHUB_SHA', 'latest')
        container_image = f"{dashi_repository.repository_uri}:{image_tag}"

        # Create a Fargate task definition for the Dashi app
        task_definition = ecs.FargateTaskDefinition(
            self,
            "DashiTaskDef",
            cpu=256,
            memory_limit_mib=512,
        )

        # Add a container to the task definition using the Docker image for the Dashi app
        dashi_container = task_definition.add_container(
            "DashiContainer",
            image=ecs.ContainerImage.from_registry(container_image),
            command=["/app/bin/dashi-start.sh"],
            port_mappings=[ecs.PortMapping(container_port=5000)],
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(rds_secret, "username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(rds_secret, "password"),
                "DB_NAME": ecs.Secret.from_secrets_manager(rds_secret, "dbname"),
                "CIRCLE_CI_TOKEN": ecs.Secret.from_secrets_manager(
                    dashi_secret_circleci, "CIRCLE_CI_TOKEN"
                ),
                "GH_TOKEN": ecs.Secret.from_secrets_manager(
                    dashi_secret_gh, "GH_TOKEN"
                ),
            },
            environment={
                "DB_HOST": rds_instance.db_instance_endpoint_address,
                "DB_PORT": rds_instance.db_instance_endpoint_port,
            },
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="dashi-log-stream",
                log_retention=logs.RetentionDays.ONE_MONTH,
            ),
        )

        # Create a Fargate service and attach it to the load balancer listener
        service = ecs.FargateService(
            self,
            "DashiService",
            cluster=ecs.Cluster(self, "DashiCluster", vpc=vpc),
            task_definition=task_definition,
            desired_count=1,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
        )

        # create security group for periodic task
        target_security_group = ec2.SecurityGroup(
            self,
            "DashiPollerTaskSecurityGroup",
            vpc=vpc,
            description="Security group for the CI polling periodic task",
        )

        # Create a target for the CloudWatch Events rule to run the scheduled task
        target = targets.EcsTask(
            task_definition=task_definition,
            cluster=service.cluster,
            task_count=1,
            container_overrides=[
                {
                    "containerName": "DashiContainer",
                    "command": ["/app/bin/ci-poller-start.sh"],
                },
            ],
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[
                target_security_group,
            ],
        )

        # Create a CloudWatch Events rule to trigger the scheduled task
        rule = events.Rule(
            self,
            "DashiScheduleRule",
            schedule=events.Schedule.rate(Duration.seconds(1800)),
        )

        # Add the target to the CloudWatch Events rule
        rule.add_target(target)

        # Grant IAM-permissions for image download
        dashi_repository.grant_pull_push(
            service.task_definition.obtain_execution_role()
        )

        # Allow access to RDS
        # Grant to the app container and periodic task accesses to the RDS instance
        rds_instance.connections.allow_default_port_from(service.connections)
        rds_instance.connections.allow_default_port_from(target_security_group)

        # Route traffic
        https_listener.add_targets(
            "DashiServiceTarget",
            port=5000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[
                service.load_balancer_target(
                    container_name="DashiContainer",
                    container_port=5000,
                )
            ],
            health_check=elbv2.HealthCheck(
                path="/",
                port="5000",
            ),
        )
