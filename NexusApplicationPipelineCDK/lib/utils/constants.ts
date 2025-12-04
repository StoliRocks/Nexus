import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Architecture } from 'aws-cdk-lib/aws-lambda';
import { CpuArchitecture } from 'aws-cdk-lib/aws-ecs';
import { Platform } from '@amzn/pipelines';
import { Severity, SIMTicketAlarmActionProps } from '@amzn/sim-ticket-cdk-constructs';

export const SERVICE_NAME = 'Nexus';

export const TEAM_NAME = 'nexus-eng';
export const RUNBOOK_PATH_PREFIX = 'runbooks/nexus';

export const DEFAULT_LOG_GROUP_RETENTION_PERIOD = RetentionDays.THREE_MONTHS;
export const DEFAULT_ARCHITECTURE = Architecture.X86_64;
export const DEFAULT_CPU_ARCHITECTURE = CpuArchitecture.X86_64;
export const DEFAULT_PLATFORM = Platform.AL2_X86_64;
export const S3_BUCKET_STAGING = 'nexus-staging-';
export const S3_BUCKET_OUTPUT = 'nexus-output-';
export const VPC_SUBNET_IP_ADDRESS = '10.0.0.0/16';

export const NEXUS_REST_API_NAME = 'Nexus Gateway';
