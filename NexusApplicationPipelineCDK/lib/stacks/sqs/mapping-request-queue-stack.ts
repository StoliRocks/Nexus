import { DeploymentStack, SoftwareType } from '@amzn/pipelines';
import { Construct } from 'constructs';
import { Duration, RemovalPolicy, Tags } from 'aws-cdk-lib';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { SqsStackProps } from '../../props/SqsStackProps';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { Alarm, ComparisonOperator, TreatMissingData } from 'aws-cdk-lib/aws-cloudwatch';

/**
 * Stack for SQS-based mapping request processing with DLQ support.
 *
 * Architecture:
 * API Handler -> MappingRequestQueue -> SQS Trigger Lambda -> Step Functions
 *                      |
 *                      v (on failure)
 *               MappingRequestDLQ -> DLQ Redrive Lambda -> MappingRequestQueue
 *
 * This provides durability for mapping requests - if Step Functions fails
 * due to a bug requiring a code fix, the request is preserved in the DLQ
 * and can be retried after deployment.
 */
export class MappingRequestQueueStack extends DeploymentStack {
  public readonly mappingRequestQueue: sqs.Queue;
  public readonly mappingRequestDLQ: sqs.Queue;
  public readonly sqsTriggerLambda: lambda.Function;
  public readonly dlqRedriveLambda: lambda.Function;
  public readonly dlqAlarm: Alarm;

  constructor(scope: Construct, id: string, props: SqsStackProps) {
    super(scope, id, {
      env: props.env,
      description: 'Stack for SQS-based mapping request queue with DLQ support.',
      stackName: id,
      softwareType: SoftwareType.INFRASTRUCTURE,
    });

    // Add stack tags for cost tracking and ownership
    Tags.of(this).add('Service', 'Nexus');
    Tags.of(this).add('Team', 'nexus-eng');
    Tags.of(this).add('Stage', props.stage);
    Tags.of(this).add('CostCenter', 'nexus-sqs');
    Tags.of(this).add('Owner', 'nexus-eng@amazon.com');

    // Create Dead Letter Queue (DLQ) for failed mapping requests
    // Messages in DLQ are retained for 14 days to allow time for bug fixes
    this.mappingRequestDLQ = new sqs.Queue(this, 'MappingRequestDLQ', {
      queueName: `MappingRequestDLQ-${props.stage}`,
      retentionPeriod: Duration.days(14),
      visibilityTimeout: Duration.minutes(6),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      removalPolicy: props.isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    // Create main mapping request queue
    // Messages are sent here by AsyncAPIHandler instead of directly starting Step Functions
    this.mappingRequestQueue = new sqs.Queue(this, 'MappingRequestQueue', {
      queueName: `MappingRequestQueue-${props.stage}`,
      retentionPeriod: Duration.days(7),
      visibilityTimeout: Duration.minutes(6), // Should be 6x Lambda timeout
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      deadLetterQueue: {
        queue: this.mappingRequestDLQ,
        maxReceiveCount: 3, // After 3 failed attempts, move to DLQ
      },
      removalPolicy: props.isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
    });

    // Create SQS Trigger Lambda - consumes from queue and starts Step Functions
    this.sqsTriggerLambda = createLambdaFunctionInstance(
      this,
      `NexusSqsTriggerLambda-${props.stage}`,
      'SQSTrigger',
      'NexusSqsTriggerLambda',
      '1.0',
      'nexus_sqs_trigger_lambda.handler.lambda_handler',
      Duration.minutes(1),
      props.vpc,
    );

    // Add environment variables for SQS Trigger Lambda
    this.sqsTriggerLambda.addEnvironment('STAGE', props.stage);
    this.sqsTriggerLambda.addEnvironment('JOB_TABLE_NAME', `MappingJobs`);
    if (props.stateMachineArn) {
      this.sqsTriggerLambda.addEnvironment('STATE_MACHINE_ARN', props.stateMachineArn);
    }

    // Add SQS event source to trigger Lambda
    this.sqsTriggerLambda.addEventSource(
      new lambdaEventSources.SqsEventSource(this.mappingRequestQueue, {
        batchSize: 1, // Process one mapping request at a time
        maxBatchingWindow: Duration.seconds(0), // No batching delay
        reportBatchItemFailures: true, // Enable partial batch failure reporting
      }),
    );

    // Grant Lambda permissions to consume from SQS
    this.mappingRequestQueue.grantConsumeMessages(this.sqsTriggerLambda);

    // Grant Lambda permissions to start Step Functions execution
    this.sqsTriggerLambda.addToRolePolicy(
      new PolicyStatement({
        actions: ['states:StartExecution'],
        effect: Effect.ALLOW,
        resources: ['*'], // Will be scoped by STATE_MACHINE_ARN env var
      }),
    );

    // Grant Lambda permissions to update DynamoDB job status
    this.sqsTriggerLambda.addToRolePolicy(
      new PolicyStatement({
        actions: ['dynamodb:UpdateItem', 'dynamodb:GetItem'],
        effect: Effect.ALLOW,
        resources: [
          `arn:aws:dynamodb:${props.awsRegion}:${props.accountId}:table/MappingJobs`,
        ],
      }),
    );

    // Add CloudWatch permissions
    this.sqsTriggerLambda.addToRolePolicy(
      new PolicyStatement({
        actions: [
          'cloudwatch:PutMetricData',
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        effect: Effect.ALLOW,
        resources: ['*'],
      }),
    );

    // Create DLQ Redrive Lambda - allows manual retry of failed messages
    this.dlqRedriveLambda = createLambdaFunctionInstance(
      this,
      `NexusDlqRedriveLambda-${props.stage}`,
      'DLQRedrive',
      'NexusDlqRedriveLambda',
      '1.0',
      'nexus_dlq_redrive_lambda.handler.lambda_handler',
      Duration.minutes(5),
      props.vpc,
    );

    // Add environment variables for DLQ Redrive Lambda
    this.dlqRedriveLambda.addEnvironment('STAGE', props.stage);
    this.dlqRedriveLambda.addEnvironment('DLQ_URL', this.mappingRequestDLQ.queueUrl);
    this.dlqRedriveLambda.addEnvironment('MAIN_QUEUE_URL', this.mappingRequestQueue.queueUrl);

    // Grant DLQ Redrive Lambda permissions
    this.mappingRequestDLQ.grantConsumeMessages(this.dlqRedriveLambda);
    this.mappingRequestQueue.grantSendMessages(this.dlqRedriveLambda);

    // Add CloudWatch permissions to DLQ Redrive Lambda
    this.dlqRedriveLambda.addToRolePolicy(
      new PolicyStatement({
        actions: [
          'cloudwatch:PutMetricData',
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents',
        ],
        effect: Effect.ALLOW,
        resources: ['*'],
      }),
    );

    // Create CloudWatch alarm for DLQ messages
    // This alerts the team when messages are landing in the DLQ
    this.dlqAlarm = new Alarm(this, 'MappingRequestDLQAlarm', {
      alarmName: `MappingRequestDLQ-MessagesVisible-${props.stage}`,
      alarmDescription:
        'Alarm when mapping requests fail and land in DLQ. ' +
        'Investigate failures and redrive after fix.',
      metric: this.mappingRequestDLQ.metricApproximateNumberOfMessagesVisible({
        period: Duration.minutes(1),
        statistic: 'Sum',
      }),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: TreatMissingData.NOT_BREACHING,
    });

    // Create alarm for queue backlog (messages not being processed fast enough)
    new Alarm(this, 'MappingRequestQueueBacklogAlarm', {
      alarmName: `MappingRequestQueue-Backlog-${props.stage}`,
      alarmDescription:
        'Alarm when mapping request queue has a backlog. ' +
        'May need to scale SQS trigger Lambda.',
      metric: this.mappingRequestQueue.metricApproximateNumberOfMessagesVisible({
        period: Duration.minutes(5),
        statistic: 'Average',
      }),
      threshold: 100, // Alert if more than 100 messages waiting
      evaluationPeriods: 3,
      comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: TreatMissingData.NOT_BREACHING,
    });

    // Create alarm for message age (messages sitting too long)
    new Alarm(this, 'MappingRequestQueueAgeAlarm', {
      alarmName: `MappingRequestQueue-MessageAge-${props.stage}`,
      alarmDescription:
        'Alarm when messages in queue are too old. ' +
        'Processing may be stuck or backed up.',
      metric: this.mappingRequestQueue.metricApproximateAgeOfOldestMessage({
        period: Duration.minutes(5),
        statistic: 'Maximum',
      }),
      threshold: 3600, // 1 hour in seconds
      evaluationPeriods: 1,
      comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: TreatMissingData.NOT_BREACHING,
    });
  }
}
