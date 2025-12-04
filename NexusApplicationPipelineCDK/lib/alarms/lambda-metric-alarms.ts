import { Construct } from 'constructs';
import { Alarm, ComparisonOperator, MathExpression, Metric, TreatMissingData } from 'aws-cdk-lib/aws-cloudwatch';
import { Duration } from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { createNexusSIMAlarmAction } from './alarm-actions';
import { Severity } from '@amzn/sim-ticket-cdk-constructs';
import { generateQualifiedAlarmName } from './alarm-utils';

export class LambdaMetricAlarms {
  public sev2Alarms: Set<Alarm> = new Set<Alarm>();
  public sev3Alarms: Set<Alarm> = new Set<Alarm>();

  constructor(
    scope: Construct,
    lambdaFunction: lambda.Function,
    lambdaAlias: lambda.Alias,
    isProd: boolean,
    stage: string,
    awsRegion: string,
  ) {
    const newFunctionVersionSuccessRateMetric = new MathExpression({
      label: 'Success Rate',
      expression: '100 - 100*error/invocations',
      period: Duration.minutes(1),
      usingMetrics: {
        error: lambdaFunction.metricErrors({
          dimensionsMap: {
            FunctionName: lambdaFunction.functionName,
            ExecutedVersion: lambdaFunction.currentVersion.version,
            Resource: `${lambdaFunction.functionName}:${lambdaAlias.aliasName}`,
          },
        }),
        invocations: lambdaFunction.metricInvocations({
          dimensionsMap: {
            FunctionName: lambdaFunction.functionName,
            ExecutedVersion: lambdaFunction.currentVersion.version,
            Resource: `${lambdaFunction.functionName}:${lambdaAlias.aliasName}`,
          },
        }),
      },
    });

    const overallFunctionSuccessRateMetric = new MathExpression({
      label: 'Success Rate',
      expression: '100 - 100*error/invocations',
      period: Duration.minutes(1),
      usingMetrics: {
        error: lambdaAlias.metricErrors(),
        invocations: lambdaAlias.metricInvocations(),
      },
    });

    // Define success rate alarms
    const sev2SuccessRateAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${lambdaFunction.functionName}_SuccessRateAlarm`, 'Sev2', stage, awsRegion),
      {
        threshold: 95,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        metric: newFunctionVersionSuccessRateMetric,
        // New version may have low or even no traffic to begin with,
        // it might be unsafe to consider missing data as breaching.
        treatMissingData: TreatMissingData.NOT_BREACHING,
      },
    );

    sev2SuccessRateAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev2Alarms.add(sev2SuccessRateAlarm);

    const sev3SuccessRateAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${lambdaFunction.functionName}_SuccessRateAlarm`, 'Sev3', stage, awsRegion),
      {
        threshold: 80,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        metric: newFunctionVersionSuccessRateMetric,
        // New version may have low or even no traffic to begin with,
        // it might be unsafe to consider missing data as breaching.
        treatMissingData: TreatMissingData.NOT_BREACHING,
      },
    );

    sev3SuccessRateAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev3Alarms.add(sev2SuccessRateAlarm);

    // Non-prod stages may have zero traffic and may block deployment unnecessarily, thus
    // we only apply overall success rate alarm in prod.
    if (isProd) {
      const sev2OverallFunctionSuccessRateAlarm = new Alarm(
        scope,
        generateQualifiedAlarmName(
          `${lambdaFunction.functionName}_OverallFunctionSuccessRateAlarm`,
          'Sev2',
          stage,
          awsRegion,
        ),
        {
          threshold: 99,
          comparisonOperator: ComparisonOperator.LESS_THAN_THRESHOLD,
          evaluationPeriods: 3,
          datapointsToAlarm: 2,
          metric: overallFunctionSuccessRateMetric,
          treatMissingData: TreatMissingData.NOT_BREACHING,
        },
      );
      this.sev2Alarms.add(sev2OverallFunctionSuccessRateAlarm);
    }

    const sev2HighCPUUsageAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${lambdaFunction.functionName}_HighCPUAlarm`, 'Sev2', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/Lambda',
          metricName: 'CPUUtilization',
          statistic: 'Average',
          period: Duration.minutes(5),
        }),
        threshold: 95,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `${lambdaFunction.functionName} CPU usage is above 80%`,
      },
    );

    sev2HighCPUUsageAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev2Alarms.add(sev2HighCPUUsageAlarm);

    const sev3HighCPUUsageAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${lambdaFunction.functionName}_HighCPUAlarm`, 'Sev3', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/Lambda',
          metricName: 'CPUUtilization',
          statistic: 'Average',
          period: Duration.minutes(5),
        }),
        threshold: 80,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `${lambdaFunction.functionName} CPU usage is above 80%`,
      },
    );

    sev3HighCPUUsageAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev3Alarms.add(sev3HighCPUUsageAlarm);
  }

  public getSev2Alarms(): Set<Alarm> {
    return this.sev2Alarms;
  }
}
