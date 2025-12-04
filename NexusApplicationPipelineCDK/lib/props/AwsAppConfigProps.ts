import { DeploymentEnvironment } from '@amzn/pipelines';

export interface AwsAppConfigProps {
  readonly serviceName: string;
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly region: string;
  readonly awsRegion: string;
  readonly computeEnvironmentIdentifier: string;
}
