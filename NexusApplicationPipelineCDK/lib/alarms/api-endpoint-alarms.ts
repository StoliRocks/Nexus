import { Construct } from 'constructs';
import { NEXUS_REST_API_NAME, RUNBOOK_PATH_PREFIX, SERVICE_NAME, TEAM_NAME } from '../utils/constants';
import { Alarm, DimensionsMap, MathExpression, Metric } from 'aws-cdk-lib/aws-cloudwatch';
import { API_RESOURCE_SET, ApiResource } from '../utils/api-resource';
import { Duration } from 'aws-cdk-lib';
import { DeploymentEnvironment } from '@amzn/pipelines';
import { API_ALARM_THRESHOLDS } from './thresholds/api-alarm-threshold';
import { Severity } from '@amzn/sim-ticket-cdk-constructs';
import { createNexusSIMAlarmAction } from './alarm-actions';
import { generateQualifiedAlarmName } from './alarm-utils';

export class ApiEndpointAlarms {
  constructor(scope: Construct, env: DeploymentEnvironment, stage: string, awsRegion: string) {
    API_RESOURCE_SET.forEach((apiResource) => {
      if (API_ALARM_THRESHOLDS[stage] && API_ALARM_THRESHOLDS[stage][awsRegion]) {
        const regionMap = API_ALARM_THRESHOLDS[stage][awsRegion];
        if (regionMap.has(apiResource)) {
          this.createAlarmOnApiEndpoints(scope, apiResource, stage, awsRegion, env);
        }
      }
    });
  }

  // TODO: Change severity on all alarms before launch.
  private createAlarmOnApiEndpoints(
    scope: Construct,
    resource: ApiResource,
    stage: string,
    awsRegion: string,
    env: DeploymentEnvironment,
  ) {
    const thresholds = API_ALARM_THRESHOLDS[stage][awsRegion].get(resource);

    if (!thresholds) {
      return;
    }

    const errorRateWarning = thresholds['ERROR_RATE']['Warning'];
    const errorRateCritical = thresholds['ERROR_RATE']['Critical'];

    const errorCountWarning = thresholds['ERROR_COUNT']['Warning'];
    const errorCountCritical = thresholds['ERROR_COUNT']['Critical'];

    // Base dimensions for the API resource
    const resourceDimensions: DimensionsMap = {
      ApiName: NEXUS_REST_API_NAME,
      Stage: stage,
      Method: resource.method,
      Resource: resource.path,
    };

    // Create error count metric for the resource
    const error5xxMetric = new Metric({
      namespace: 'AWS/ApiGateway',
      metricName: '5XXError',
      dimensionsMap: resourceDimensions,
      statistic: 'Sum',
      period: Duration.minutes(5),
    });

    // Create error rate metric for the resource
    const requestCountMetric = new Metric({
      namespace: 'AWS/ApiGateway',
      metricName: 'Count',
      dimensionsMap: resourceDimensions,
      statistic: 'Sum',
      period: Duration.minutes(5),
    });

    // Calculate error rate using metric math
    const errorRateMetric = new MathExpression({
      expression: '(errors / requests) * 100',
      usingMetrics: {
        errors: error5xxMetric,
        requests: requestCountMetric,
      },
      period: Duration.minutes(5),
    });

    // SEV-2 Error Rate Alarm (>5% error rate)
    const sev2RateAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${resource.method}-${resource.path}-Rate`, 'Sev2', stage, awsRegion),
      {
        metric: errorRateMetric,
        threshold: errorRateCritical.threshold, // 5% error rate
        evaluationPeriods: errorRateCritical.threshold,
        datapointsToAlarm: errorRateCritical.datapointsToAlarm,
        comparisonOperator: errorRateCritical.comparisonOperator,
        treatMissingData: errorRateCritical.treatMissingData,
        alarmDescription: JSON.stringify({
          severity: 'SEV2',
          category: 'AVAILABILITY',
          service: SERVICE_NAME,
          environment: env,
          resource: resource.path,
          method: resource.method,
          impact: `High 5XX error rate on ${resource.method} ${resource.path}`,
          runbook: `${RUNBOOK_PATH_PREFIX}/api-5xx-errors`,
          teamOwner: TEAM_NAME,
        }),
      },
    );

    sev2RateAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));

    // SEV-3 Error Rate Alarm
    const sev3RateAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${resource.method}-${resource.path}-Rate`, 'Sev3', stage, awsRegion),
      {
        metric: errorRateMetric,
        threshold: errorRateWarning.threshold,
        evaluationPeriods: errorRateWarning.threshold,
        datapointsToAlarm: errorRateWarning.datapointsToAlarm,
        comparisonOperator: errorRateWarning.comparisonOperator,
        treatMissingData: errorRateWarning.treatMissingData,
        alarmDescription: JSON.stringify({
          severity: 'SEV3',
          category: 'AVAILABILITY',
          service: SERVICE_NAME,
          environment: env,
          resource: resource.path,
          method: resource.method,
          impact: `High 5XX error rate on ${resource.method} ${resource.path}`,
          runbook: `${RUNBOOK_PATH_PREFIX}/api-5xx-errors`,
          teamOwner: TEAM_NAME,
        }),
      },
    );

    sev3RateAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));

    // SEV-2 Error Count Alarm
    const sev2CountAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${resource.method}-${resource.path}-Count`, 'Sev2', stage, awsRegion),
      {
        metric: error5xxMetric,
        threshold: errorCountCritical.threshold,
        evaluationPeriods: errorCountCritical.evaluationPeriods,
        datapointsToAlarm: errorCountCritical.datapointsToAlarm,
        comparisonOperator: errorCountCritical.comparisonOperator,
        treatMissingData: errorCountCritical.treatMissingData,
        alarmDescription: JSON.stringify({
          severity: 'SEV2',
          category: 'AVAILABILITY',
          service: SERVICE_NAME,
          environment: env,
          resource: resource.path,
          method: resource.method,
          impact: `High number of 5XX errors on ${resource.method} ${resource.path}`,
          runbook: `${RUNBOOK_PATH_PREFIX}/api-5xx-errors`,
          teamOwner: TEAM_NAME,
        }),
      },
    );

    sev2CountAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));

    // SEV-3 Error Count Alarm
    const sev3CountAlarm = new Alarm(
      scope,
      generateQualifiedAlarmName(`${resource.method}-${resource.path}-Count`, 'Sev3', stage, awsRegion),
      {
        metric: error5xxMetric,
        threshold: errorCountWarning.threshold,
        evaluationPeriods: errorCountWarning.evaluationPeriods,
        datapointsToAlarm: errorCountWarning.datapointsToAlarm,
        comparisonOperator: errorCountWarning.comparisonOperator,
        treatMissingData: errorCountWarning.treatMissingData,
        alarmDescription: JSON.stringify({
          severity: 'SEV3',
          category: 'AVAILABILITY',
          service: SERVICE_NAME,
          environment: env,
          resource: resource.path,
          method: resource.method,
          impact: `High number of 5XX errors on ${resource.method} ${resource.path}`,
          runbook: `${RUNBOOK_PATH_PREFIX}/api-5xx-errors`,
          teamOwner: TEAM_NAME,
        }),
      },
    );

    sev3CountAlarm.addAlarmAction(createNexusSIMAlarmAction(Severity.SEV5));
  }
}
