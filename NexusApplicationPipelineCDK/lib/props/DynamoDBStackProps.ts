import { DeploymentEnvironment } from '@amzn/pipelines';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';

export interface DynamoDBStackProps {
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly region: string;
  readonly awsRegion: string;
  readonly isProd: boolean;
  readonly tableName: string;
  readonly partitionKey: string;
  readonly sortKey?: string;
  readonly globalSecondaryIndexes?: dynamodb.GlobalSecondaryIndexProps[];
  readonly accountId: string;
  readonly arns?: string[];
  /** Enable DynamoDB Streams for trigger-based workflows */
  readonly streamEnabled?: boolean;
  /** Stream view type (default: NEW_AND_OLD_IMAGES) */
  readonly streamViewType?: dynamodb.StreamViewType;
}
