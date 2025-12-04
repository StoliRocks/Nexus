import { Duration } from 'aws-cdk-lib';
import { IVpc } from 'aws-cdk-lib/aws-ec2';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { BrazilPackage, LambdaAsset } from '@amzn/pipelines';
import { DEFAULT_BRAZIL_PYTHON_RUNTIME } from '../runtime/runtime';
import { createLogGroup } from './log-groups';
import { Construct } from 'constructs';

export function createLambdaFunctionInstance(
  scope: Construct,
  functionName: string,
  componentName: string,
  brazilPackageName: string,
  brazilPackageVersion: string,
  handler: string,
  timeoutInMinutes: Duration,
  vpc: IVpc,
): lambda.Function {
  return new lambda.Function(scope, functionName, {
    functionName: functionName,
    description: `Timestamp: ${new Date().toISOString()}`,
    code: LambdaAsset.fromBrazil({
      brazilPackage: BrazilPackage.fromString(`${brazilPackageName}-${brazilPackageVersion}`),
      componentName: componentName,
    }),
    handler: handler,
    runtime: DEFAULT_BRAZIL_PYTHON_RUNTIME,
    timeout: timeoutInMinutes,
    logGroup: createLogGroup(scope, `${functionName}LogGroup`),
    vpc: vpc,
  });
}
