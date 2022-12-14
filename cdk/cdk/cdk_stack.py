import aws_cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_s3 as s3,
    CfnOutput, RemovalPolicy, aws_route53,
)
from aws_cdk.aws_s3 import BlockPublicAccess
from constructs import Construct


class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # use default vpc for avoid additional costs
        vpc = ec2.Vpc.from_lookup(self, "VPC",
                                  is_default=True
                                  )

        # security group for dashi instance
        security_group = ec2.SecurityGroup(self, "SG",
                                           vpc=vpc,
                                           security_group_name="dashi-sg"
                                           )

        # http connection
        security_group.add_ingress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"),
            ec2.Port.tcp(80)
        )

        # https connection
        security_group.add_ingress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"),
            ec2.Port.tcp(443)
        )

        # add ip for ssh connect
        my_ip = self.node.try_get_context("my_ip")
        if my_ip is not None:
            security_group.add_ingress_rule(
                ec2.Peer.ipv4("{}/32".format(my_ip)),
                ec2.Port.tcp(22)
            )

        # pre-install docker-ce
        user_data = ec2.UserData.for_linux()
        user_data.add_commands("apt update")
        user_data.add_commands("apt install -y ca-certificates curl gnupg lsb-release")
        user_data.add_commands("mkdir -p /etc/apt/keyrings")
        user_data.add_commands("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg")
        user_data.add_commands("echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] "
                               "https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" | sudo tee "
                               "/etc/apt/sources.list.d/docker.list > /dev/null")
        user_data.add_commands("chmod a+r /etc/apt/keyrings/docker.gpg")
        user_data.add_commands("apt update")
        user_data.add_commands("apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin awscli")
        user_data.add_commands("usermod -a -G docker ubuntu")
        user_data.add_commands("ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin")

        # dashi instance
        dashi_instance = ec2.Instance(self, "Instance",
                                      vpc=vpc,
                                      instance_type=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
                                      machine_image=ec2.MachineImage.generic_linux({
                                          "eu-west-1": "ami-0a3a484e07ffb6be7"
                                      }),
                                      block_devices=[ec2.BlockDevice(
                                          device_name="/dev/sda1",
                                          volume=ec2.BlockDeviceVolume.ebs(50)
                                      )],
                                      key_name="dashi-key",
                                      instance_name="dashi",
                                      security_group=security_group,
                                      user_data=user_data
                                      )

        elastic_ip = ec2.CfnEIP(self, "EIP",
                                domain="vpc",
                                instance_id=dashi_instance.instance_id
                                )

        docker_repository = ecr.Repository(self, "DockerRepo",
                                           repository_name="dashi"
                                           )
        docker_repository.add_lifecycle_rule(max_image_count=10, description="Limit images count")
        docker_repository.grant_pull(dashi_instance)
        docker_repository.apply_removal_policy(RemovalPolicy.DESTROY)

        zone = aws_route53.HostedZone.from_lookup(self, "zone",
                                                  domain_name="cto.redislabs.com"
                                                  )

        aws_route53.ARecord(self, "dnsRecord",
                            target=aws_route53.RecordTarget.from_ip_addresses(
                                elastic_ip.ref),
                            zone=zone,
                            record_name="dashi",
                            ttl=aws_cdk.Duration.minutes(60)
                            )

        buckup_bucket = s3.Bucket(self, "BuckupBucket",
                                  bucket_name="redis-dashi-buckup",
                                  block_public_access=BlockPublicAccess.BLOCK_ALL,
                                  auto_delete_objects=True,
                                  removal_policy=RemovalPolicy.DESTROY,
                                  )

        buckup_bucket.grant_read_write(dashi_instance)

        CfnOutput(self, "DashiRepo", value=docker_repository.repository_uri)

        CfnOutput(self, "DashiIp", value=elastic_ip.ref)
        CfnOutput(self, "DashiBuckupBucket", value=buckup_bucket.bucket_name)
