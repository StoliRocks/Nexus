import { ComparisonOperator, CreateAlarmOptions, TreatMissingData } from 'aws-cdk-lib/aws-cloudwatch';

export const api_availability_thresholds: Record<string, Record<string, Record<string, CreateAlarmOptions>>> = {
  alpha: {
    'us-east-1': {},
  },
  beta: {
    'us-east-1': {},
  },
  gamma: {
    'us-east-1': {
      Warning: {
        threshold: 95,
        comparisonOperator: ComparisonOperator.LESS_THAN_THRESHOLD,
        evaluationPeriods: 3,
        treatMissingData: TreatMissingData.NOT_BREACHING,
      },
    },
  },
  prod: {
    'us-east-1': {
      Warning: {
        threshold: 90,
        comparisonOperator: ComparisonOperator.LESS_THAN_THRESHOLD,
        evaluationPeriods: 3,
        treatMissingData: TreatMissingData.NOT_BREACHING,
      },
      Critical: {
        threshold: 95,
        comparisonOperator: ComparisonOperator.LESS_THAN_THRESHOLD,
        evaluationPeriods: 3,
        treatMissingData: TreatMissingData.NOT_BREACHING,
      },
    },
  },
};
