import { DeploymentEnvironment } from '@amzn/pipelines';

export interface VpcStackProps {
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly cidr?: string;
  readonly isProd: boolean;
  readonly maxAzs: number;
}
