import { DeploymentEnvironment } from '@amzn/pipelines';
import { IVpc } from 'aws-cdk-lib/aws-ec2';

export interface SqsStackProps {
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly region: string;
  readonly awsRegion: string;
  readonly isProd: boolean;
  readonly accountId: string;
  readonly vpc: IVpc;
  readonly stateMachineArn?: string;
}
