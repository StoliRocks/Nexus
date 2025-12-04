import { LogGroup } from 'aws-cdk-lib/aws-logs';
import { DEFAULT_LOG_GROUP_RETENTION_PERIOD } from './constants';
import { RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export function createLogGroup(scope: Construct, id: string) {
  return new LogGroup(scope, id, {
    logGroupName: id,
    removalPolicy: RemovalPolicy.RETAIN,
    retention: DEFAULT_LOG_GROUP_RETENTION_PERIOD,
  });
}
