import { API_RESOURCE_DELETE_SESSION_ID, ApiResource } from '../../utils/api-resource';
import { ComparisonOperator, TreatMissingData } from 'aws-cdk-lib/aws-cloudwatch';

export interface CustomThreshold {
  threshold: number;
  evaluationPeriods: number;
  datapointsToAlarm: number;
  comparisonOperator: ComparisonOperator;
  treatMissingData: TreatMissingData;
}

const DEFAULT_ERROR_RATE_WARNING_THRESHOLD: CustomThreshold = {
  threshold: 3,
  evaluationPeriods: 2,
  datapointsToAlarm: 2,
  comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: TreatMissingData.NOT_BREACHING,
};

const DEFAULT_ERROR_RATE_CRITICAL_THRESHOLD: CustomThreshold = {
  threshold: 5,
  evaluationPeriods: 2,
  datapointsToAlarm: 2,
  comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: TreatMissingData.NOT_BREACHING,
};

const DEFAULT_ERROR_COUNT_WARNING_THRESHOLD: CustomThreshold = {
  threshold: 3,
  evaluationPeriods: 2,
  datapointsToAlarm: 2,
  comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: TreatMissingData.NOT_BREACHING,
};

const DEFAULT_ERROR_COUNT_CRITICAL_THRESHOLD: CustomThreshold = {
  threshold: 5,
  evaluationPeriods: 2,
  datapointsToAlarm: 2,
  comparisonOperator: ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: TreatMissingData.NOT_BREACHING,
};

export const API_ALARM_THRESHOLDS: Record<
  string,
  Record<string, Map<ApiResource, Record<string, Record<string, CustomThreshold>>>>
> = {
  alpha: {},
  beta: {},
  gamma: {},
  'one-box': {},
  prod: {
    'us-east-1': new Map<ApiResource, Record<string, Record<string, CustomThreshold>>>([
      [
        API_RESOURCE_DELETE_SESSION_ID,
        {
          ERROR_RATE: {
            Warning: DEFAULT_ERROR_RATE_WARNING_THRESHOLD,
            Critical: DEFAULT_ERROR_RATE_CRITICAL_THRESHOLD,
          },
          ERROR_COUNT: {
            Warning: DEFAULT_ERROR_COUNT_WARNING_THRESHOLD,
            Critical: DEFAULT_ERROR_COUNT_CRITICAL_THRESHOLD,
          },
        },
      ],
    ]),
  },
};
