import { Stack, StackProps, Duration, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import { EnvNameType, projectName, s3BucketProps } from "../constant";
import { BlockPublicAccess, Bucket, BucketEncryption, ObjectOwnership } from "aws-cdk-lib/aws-s3";
import { setSecureTransport } from "../utility";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as ecrAssets from "aws-cdk-lib/aws-ecr-assets";
import * as path from "path";
import { NagSuppressions } from "cdk-nag";

interface MedicalDeviceFargateStackProps extends StackProps {
  envName: EnvNameType;
}

export class MedicalDeviceFargateStack extends Stack {
  constructor(scope: Construct, id: string, props: MedicalDeviceFargateStackProps) {
    super(scope, id, props);

    const accessLogBucket = new Bucket(this, `${projectName}-access-bucket-access-logs`, {
      objectOwnership: ObjectOwnership.OBJECT_WRITER,
      encryption: BucketEncryption.S3_MANAGED,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      enforceSSL: true,
      ...s3BucketProps,
    });

    setSecureTransport(accessLogBucket);

    const flowLogBucket = new Bucket(this, `${projectName}-flow-log-bucket`, {
      objectOwnership: ObjectOwnership.OBJECT_WRITER,
      encryption: BucketEncryption.S3_MANAGED,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      serverAccessLogsBucket: accessLogBucket,
      serverAccessLogsPrefix: `${projectName}-vpc-bucket-access-logs`,
      versioned: true,
      enforceSSL: true,
      ...s3BucketProps,
    });

    setSecureTransport(flowLogBucket);

    flowLogBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.ServicePrincipal('vpc-flow-logs.amazonaws.com')],
        actions: ['s3:PutObject'],
        resources: [`${flowLogBucket.bucketArn}/*`],
        conditions: {
          StringEquals: {
            'aws:SourceAccount': process.env.CDK_DEFAULT_ACCOUNT,
          },
          ArnLike: {
            'aws:SourceArn': `arn:aws:ec2:${process.env.CDK_DEFAULT_REGION}:${process.env.CDK_DEFAULT_ACCOUNT}:vpc-flow-log/*`,
          },
        },
      })
    );

    // Define the VPC
    const vpc = new ec2.Vpc(this, `${projectName}-vpc`, {
      maxAzs: 2,
      natGateways: 1,
    });

    new ec2.CfnFlowLog(this, `${projectName}-vpc-flow-log`, {
      resourceId: vpc.vpcId,
      resourceType: "VPC",
      trafficType: "ALL",
      logDestinationType: "s3",
      logDestination: flowLogBucket.bucketArn,
    });

    // Create an ECS cluster
    const cluster = new ecs.Cluster(this, `${projectName}-cluster`, {
      vpc,
      containerInsights: true,
    });

    // Create a log group for the container
    const logGroup = new logs.LogGroup(this, `${projectName}-service-logs`, {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Create a task execution role
    const executionRole = new iam.Role(this, `${projectName}-task-execution-role`, {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managedPolicies: [iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AmazonECSTaskExecutionRolePolicy")],
    });

    // Create a task role with permissions to invoke Bedrock APIs
    const taskRole = new iam.Role(this, `${projectName}-task-role`, {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });

    // Add permissions for the task to invoke Bedrock APIs
    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel", 
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:Converse",
          "bedrock:ConverseStream"
        ],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0`,
          `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-*`,
        ],
      }),
    );

    // Create a task definition
    const taskDefinition = new ecs.FargateTaskDefinition(this, `${projectName}-task-definition`, {
      memoryLimitMiB: 4096,
      cpu: 2048,
      executionRole,
      taskRole,
      runtimePlatform: {
        cpuArchitecture: ecs.CpuArchitecture.X86_64,
        operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
      },
    });

    // Create Docker image asset from current directory
    const dockerAsset = new ecrAssets.DockerImageAsset(this, `${projectName}-image`, {
      directory: path.resolve(__dirname, "../.."),
      file: "./Dockerfile",
    });

    // Add container to the task definition
    taskDefinition.addContainer(`${projectName}-container`, {
      image: ecs.ContainerImage.fromDockerImageAsset(dockerAsset),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "medical-device-service",
        logGroup,
      }),
      environment: {
        LOG_LEVEL: "INFO",
      },
      portMappings: [
        {
          containerPort: 8501, // Streamlit port
          protocol: ecs.Protocol.TCP,
        },
      ],
    });

    // Create security group for the service
    const serviceSecurityGroup = new ec2.SecurityGroup(this, `${projectName}-service-sg`, {
      vpc,
      description: "Security group for Medical Device Streamlit Service",
      allowAllOutbound: true,
    });

    // Create a Fargate service
    const service = new ecs.FargateService(this, `${projectName}-service`, {
      cluster,
      taskDefinition,
      desiredCount: 1, // Single instance for Streamlit
      assignPublicIp: false,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [serviceSecurityGroup],
      minHealthyPercent: 0, // Allow zero healthy for single instance
      maxHealthyPercent: 200,
      healthCheckGracePeriod: Duration.seconds(600),
    });

    // Create an Application Load Balancer
    const lb = new elbv2.ApplicationLoadBalancer(this, `${projectName}-alb`, {
      vpc,
      internetFacing: true,
    });

    // Allow ALB to communicate with service
    serviceSecurityGroup.addIngressRule(
      ec2.Peer.securityGroupId(lb.connections.securityGroups[0].securityGroupId),
      ec2.Port.tcp(8501),
      "Allow ALB to access Streamlit"
    );

    // Create a listener
    const listener = lb.addListener(`${projectName}-listener`, {
      port: 80,
    });

    // Add target group to the listener
    listener.addTargets(`${projectName}-targets`, {
      port: 8501,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [service],
      healthCheck: {
        path: "/",
        interval: Duration.seconds(120),
        timeout: Duration.seconds(30),
        healthyHttpCodes: "200",
        healthyThresholdCount: 2,
        unhealthyThresholdCount: 10,
      },
      deregistrationDelay: Duration.seconds(30),
    });

    // Output the load balancer DNS name
    this.exportValue(lb.loadBalancerDnsName, {
      name: `${projectName}-service-endpoint`,
      description: "The DNS name of the load balancer for the Medical Device Service",
    });

    // CDK NAG suppressions
    NagSuppressions.addResourceSuppressions(executionRole, [
      {
        id: "AwsSolutions-IAM4",
        reason: "AmazonECSTaskExecutionRolePolicy is used intentionally.",
      },
    ]);

    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${projectName}FargateStack/${projectName}-task-execution-role/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "ECS task execution role requires wildcard permissions for CloudWatch logs.",
          appliesTo: ['Resource::*'],
        },
      ]
    );

    NagSuppressions.addResourceSuppressionsByPath(
      this,
      `/${projectName}FargateStack/${projectName}-task-role/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Bedrock requires wildcard permissions for Claude model variants.",
          appliesTo: [
            'Resource::arn:aws:bedrock:<AWS::Region>::foundation-model/anthropic.claude-*'
          ],
        },
      ]
    );

    NagSuppressions.addResourceSuppressions(taskDefinition, [
      {
        id: 'AwsSolutions-ECS2',
        reason: 'Environment variables used are non-sensitive and needed for container behavior.',
      },
    ]);

    NagSuppressions.addResourceSuppressions(lb, [
      {
        id: 'AwsSolutions-ELB2',
        reason: 'ALB access logs cannot be enabled on region agnostic stacks. Use VPC flow logs',
      },
    ]);

    NagSuppressions.addResourceSuppressions(lb.connections.securityGroups[0], [
      {
        id: 'AwsSolutions-EC23',
        reason: 'ALB requires public internet access for web application.',
      },
    ]);
  }
}