import { DeploymentStack, SoftwareType } from '@amzn/pipelines';
import { Construct } from 'constructs';
import { DynamoDBStackProps } from '../../props/DynamoDBStackProps';
import { RemovalPolicy } from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { ArnPrincipal, Effect, PolicyDocument, PolicyStatement } from 'aws-cdk-lib/aws-iam';

export class DynamodbStack extends DeploymentStack {
  constructor(scope: Construct, id: string, props: DynamoDBStackProps) {
    super(scope, id, {
      env: props.env,
      description: 'Stack to create DynamoDB instances.',
      stackName: id,
      softwareType: SoftwareType.INFRASTRUCTURE,
    });

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
      removalPolicy: props.isProd ? RemovalPolicy.DESTROY : RemovalPolicy.RETAIN,
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

    const dynamoDBTable = new dynamodb.Table(this, props.tableName, tableProps);
    if (props.globalSecondaryIndexes) {
      props.globalSecondaryIndexes.forEach((globalSecondaryIndex) => {
        dynamoDBTable.addGlobalSecondaryIndex(globalSecondaryIndex);
      });
    }
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
