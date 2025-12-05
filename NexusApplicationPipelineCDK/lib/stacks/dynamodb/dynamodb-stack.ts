import { DeploymentStack, SoftwareType } from '@amzn/pipelines';
import { Construct } from 'constructs';
import { DynamoDBStackProps } from '../../props/DynamoDBStackProps';
import { RemovalPolicy, Tags } from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { ArnPrincipal, Effect, PolicyDocument, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { DynamoDbMetricAlarms } from '../../alarms/dynamodb-metric-alarms';

export class DynamodbStack extends DeploymentStack {
  public readonly table: dynamodb.Table;
  public readonly alarms: DynamoDbMetricAlarms;

  constructor(scope: Construct, id: string, props: DynamoDBStackProps) {
    super(scope, id, {
      env: props.env,
      description: 'Stack to create DynamoDB instances.',
      stackName: id,
      softwareType: SoftwareType.INFRASTRUCTURE,
    });

    // Add stack tags for cost tracking and ownership
    Tags.of(this).add('Service', 'Nexus');
    Tags.of(this).add('Team', 'nexus-eng');
    Tags.of(this).add('Stage', props.stage);
    Tags.of(this).add('CostCenter', 'nexus-database');
    Tags.of(this).add('Owner', 'nexus-eng@amazon.com');

    // Create the Document Ingestion Status table
    let tableProps: dynamodb.TableProps = {
      tableName: props.tableName,
      partitionKey: {
        name: props.partitionKey,
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'expiryTime',
      encryption: dynamodb.TableEncryption.DEFAULT,
      removalPolicy: props.isProd ? RemovalPolicy.RETAIN : RemovalPolicy.DESTROY,
      deletionProtection: true,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
    };

    const principals = this.convertToArnPrincipals(props.arns);
    if (principals.length > 0) {
      const ingestionStatusPolicy = new PolicyStatement({
        actions: [
          'dynamodb:BatchGetItem',
          'dynamodb:Query',
          'dynamodb:GetItem',
          'dynamodb:Scan',
          'dynamodb:ConditionCheckItem',
          'dynamodb:BatchWriteItem',
          'dynamodb:PutItem',
          'dynamodb:UpdateItem',
          'dynamodb:DeleteItem',
          'dynamodb:DescribeTable',
        ],
        effect: Effect.ALLOW,
        resources: [
          `arn:aws:dynamodb:${props.region}:${props.accountId}:table/${props.tableName}`,
          `arn:aws:dynamodb:${props.region}:${props.accountId}:table/${props.tableName}/index/*`,
        ],
        principals: principals,
      });

      tableProps = {
        ...tableProps,
        resourcePolicy: new PolicyDocument({
          statements: [ingestionStatusPolicy],
        }),
      };
    }

    // Add sortKey only if it exists and is not empty
    if (props.sortKey && props.sortKey.trim().length > 0) {
      tableProps = {
        ...tableProps,
        sortKey: {
          name: props.sortKey,
          type: dynamodb.AttributeType.STRING,
        },
      };
    }

    // Add DynamoDB Streams if enabled (for trigger-based workflows)
    if (props.streamEnabled) {
      tableProps = {
        ...tableProps,
        stream: props.streamViewType || dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
      };
    }

    this.table = new dynamodb.Table(this, props.tableName, tableProps);
    if (props.globalSecondaryIndexes) {
      props.globalSecondaryIndexes.forEach((globalSecondaryIndex) => {
        this.table.addGlobalSecondaryIndex(globalSecondaryIndex);
      });
    }

    // Create CloudWatch alarms for this table
    this.alarms = new DynamoDbMetricAlarms(
      this,
      this.table,
      props.tableName,
      props.isProd,
      props.stage,
      props.awsRegion,
    );
  }

  /**
   * Convert an array of ARNs to ArnPrincipal objects.
   * @param arns
   */
  convertToArnPrincipals(arns: string[] | null | undefined): ArnPrincipal[] {
    if (!arns || arns.length === 0) {
      return [];
    }

    return arns
      .filter((arn) => {
        if (!arn) {
          return false;
        }
        return arn.startsWith('arn:');
      })
      .map((arn) => new ArnPrincipal(arn));
  }
}
