import { Construct } from 'constructs';
import { Alarm, ComparisonOperator, Metric, TreatMissingData } from 'aws-cdk-lib/aws-cloudwatch';
import { Duration } from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { createNexusSIMAlarmAction } from './alarm-actions';
import { Severity } from '@amzn/sim-ticket-cdk-constructs';
import { generateQualifiedAlarmName } from './alarm-utils';

/**
 * CloudWatch alarms for DynamoDB tables.
 *
 * Creates alarms for:
 * - Read/Write throttle events
 * - System errors
 * - User errors (4xx)
 * - Consumed capacity (optional, for provisioned tables)
 */
export class DynamoDbMetricAlarms {
  public sev2Alarms: Set<Alarm> = new Set<Alarm>();
  public sev3Alarms: Set<Alarm> = new Set<Alarm>();

  constructor(
    scope: Construct,
    table: dynamodb.Table,
    tableName: string,
    isProd: boolean,
    stage: string,
    awsRegion: string,
  ) {
    // Read Throttle Events Alarm (Sev2)
    const readThrottleAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${tableName}_ReadThrottleAlarm`, 'Sev2', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/DynamoDB',
          metricName: 'ReadThrottledRequests',
          dimensionsMap: {
            TableName: tableName,
          },
          statistic: 'Sum',
          period: Duration.minutes(1),
        }),
        threshold: 1,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `DynamoDB table ${tableName} is experiencing read throttling`,
      },
    );
    readThrottleAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev2Alarms.add(readThrottleAlarm);

    // Write Throttle Events Alarm (Sev2)
    const writeThrottleAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${tableName}_WriteThrottleAlarm`, 'Sev2', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/DynamoDB',
          metricName: 'WriteThrottledRequests',
          dimensionsMap: {
            TableName: tableName,
          },
          statistic: 'Sum',
          period: Duration.minutes(1),
        }),
        threshold: 1,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `DynamoDB table ${tableName} is experiencing write throttling`,
      },
    );
    writeThrottleAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev2Alarms.add(writeThrottleAlarm);

    // System Errors Alarm (Sev2) - Internal DynamoDB errors
    const systemErrorsAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${tableName}_SystemErrorsAlarm`, 'Sev2', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/DynamoDB',
          metricName: 'SystemErrors',
          dimensionsMap: {
            TableName: tableName,
          },
          statistic: 'Sum',
          period: Duration.minutes(1),
        }),
        threshold: 1,
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `DynamoDB table ${tableName} is experiencing system errors (5xx)`,
      },
    );
    systemErrorsAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev2Alarms.add(systemErrorsAlarm);

    // User Errors Alarm (Sev3) - Client-side errors (4xx) may indicate application issues
    const userErrorsAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${tableName}_UserErrorsAlarm`, 'Sev3', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/DynamoDB',
          metricName: 'UserErrors',
          dimensionsMap: {
            TableName: tableName,
          },
          statistic: 'Sum',
          period: Duration.minutes(5),
        }),
        threshold: 10, // Allow some user errors before alarming
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `DynamoDB table ${tableName} is experiencing elevated user errors (4xx)`,
      },
    );
    userErrorsAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev3Alarms.add(userErrorsAlarm);

    // Conditional check failed alarm (Sev3) - May indicate hot partition or contention
    const conditionalCheckFailedAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${tableName}_ConditionalCheckFailedAlarm`, 'Sev3', stage, awsRegion),
      {
        metric: new Metric({
          namespace: 'AWS/DynamoDB',
          metricName: 'ConditionalCheckFailedRequests',
          dimensionsMap: {
            TableName: tableName,
          },
          statistic: 'Sum',
          period: Duration.minutes(5),
        }),
        threshold: 50, // Some conditional check failures are expected
        evaluationPeriods: 3,
        datapointsToAlarm: 2,
        comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: TreatMissingData.NOT_BREACHING,
        alarmDescription: `DynamoDB table ${tableName} has elevated conditional check failures (potential hot partition)`,
      },
    );
    conditionalCheckFailedAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
    this.sev3Alarms.add(conditionalCheckFailedAlarm);

    // Production-only: Latency alarms
    if (isProd) {
      // High read latency alarm
      const readLatencyAlarm = new Alarm(
        scope,
        generateQualifiedAlarmName(`${tableName}_ReadLatencyAlarm`, 'Sev2', stage, awsRegion),
        {
          metric: new Metric({
            namespace: 'AWS/DynamoDB',
            metricName: 'SuccessfulRequestLatency',
            dimensionsMap: {
              TableName: tableName,
              Operation: 'GetItem',
            },
            statistic: 'p99',
            period: Duration.minutes(5),
          }),
          threshold: 100, // 100ms p99 latency threshold
          evaluationPeriods: 3,
          datapointsToAlarm: 2,
          comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
          treatMissingData: TreatMissingData.NOT_BREACHING,
          alarmDescription: `DynamoDB table ${tableName} GetItem p99 latency is above 100ms`,
        },
      );
      readLatencyAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
      this.sev2Alarms.add(readLatencyAlarm);

      // High query latency alarm
      const queryLatencyAlarm = new Alarm(
        scope,
        generateQualifiedAlarmName(`${tableName}_QueryLatencyAlarm`, 'Sev2', stage, awsRegion),
        {
          metric: new Metric({
            namespace: 'AWS/DynamoDB',
            metricName: 'SuccessfulRequestLatency',
            dimensionsMap: {
              TableName: tableName,
              Operation: 'Query',
            },
            statistic: 'p99',
            period: Duration.minutes(5),
          }),
          threshold: 200, // 200ms p99 latency threshold for queries
          evaluationPeriods: 3,
          datapointsToAlarm: 2,
          comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
          treatMissingData: TreatMissingData.NOT_BREACHING,
          alarmDescription: `DynamoDB table ${tableName} Query p99 latency is above 200ms`,
        },
      );
      queryLatencyAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
      this.sev2Alarms.add(queryLatencyAlarm);
    }
  }

  public getSev2Alarms(): Set<Alarm> {
    return this.sev2Alarms;
  }

  public getSev3Alarms(): Set<Alarm> {
    return this.sev3Alarms;
  }

  public getAllAlarms(): Alarm[] {
    return [...this.sev2Alarms, ...this.sev3Alarms];
  }
}
