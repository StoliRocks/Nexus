import { StackProps } from 'aws-cdk-lib';
import { DeploymentEnvironment } from '@amzn/pipelines';
import { Alarm, Metric } from 'aws-cdk-lib/aws-cloudwatch';

export interface DashboardStackProps extends StackProps {
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly awsRegion: string;
  readonly isProd: boolean;
  readonly alarms: Alarm[];
  readonly metrics: Metric[];
}
