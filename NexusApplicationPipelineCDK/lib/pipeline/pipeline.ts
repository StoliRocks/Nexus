import { App } from 'aws-cdk-lib';
import {
  ApprovalWorkflowStep,
  BrazilPackage,
  CodeReviewVerificationApprovalWorkflowStep,
  DependencyModel,
  DeploymentEnvironment,
  DeploymentEnvironmentFactory,
  DeploymentPipeline,
  GordianKnotScannerApprovalWorkflowStep,
  Platform,
  ScanProfile,
} from '@amzn/pipelines';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { ProjectionType } from 'aws-cdk-lib/aws-dynamodb';
import { AwokeAnalysisApprovalWorkflowStep } from '@amzn/pipelines/dist/lib/approval/steps/awoke-analysis';
import { ComputeEnvironment, PIPELINE_STAGE_CONFIGS } from './pipelineStage';
import { AppConfigStack } from '../stacks/appconfig/app-config-stack';
import { VpcDeploymentStack } from '../stacks/vpc-deployment-stack';
import { DynamodbStack } from '../stacks/dynamodb/dynamodb-stack';
import { MappingRequestQueueStack } from '../stacks/sqs/mapping-request-queue-stack';
import { SERVICE_NAME } from '../utils/constants';
import { SqsStackProps } from '../props/SqsStackProps';
import { DashboardStack } from '../stacks/dashboard/dashboard-stack';
import { ApiEndpointHandlerLambdaStack } from '../stacks/apihandlers/api-endpoint-handler-lambda-stack';

// Pipeline constants
const PIPELINE_NAME = 'NexusApplicationPipeline';
const APPLICATION_ACCOUNT = '593130130809';
const VERSION_SET = 'NexusApplicationPipeline/development';
const VERSION_SET_PLATFORM = Platform.AL2_X86_64;
const BINDLE_GUID = 'amzn1.bindle.resource.lwek4d4hh56znrpdjw4q';
const PIPELINE_ID = '8773961';
const DESCRIPTION = `A CDK managed pipeline for ${SERVICE_NAME}.
This service hosts the Nexus artifacts and the pipeline deploys related stacks.
Design document is available at https://quip-amazon.com/YWiSAOYz54gJ/Nexus-High-Level-Design-Doc-Revision-4`;

// Account constants
const POSIX_GROUP = 'nexus-eng';
const TEAM_EMAIL = 'nexus-eng@amazon.com';

const VERSION_SET_APPROVAL_WORKFLOW = 'VersionSet Workflow';

export class PipelineInfrastructure {
  constructor(app: App) {
    const pipeline = new DeploymentPipeline(app, 'Pipeline', {
      account: APPLICATION_ACCOUNT,
      pipelineName: PIPELINE_NAME,
      versionSet: {
        name: VERSION_SET,
        dependencyModel: DependencyModel.BRAZIL,
      },
      versionSetPlatform: VERSION_SET_PLATFORM,
      trackingVersionSet: 'live', // Or any other version set you prefer
      bindleGuid: BINDLE_GUID,
      description: DESCRIPTION,
      pipelineId: PIPELINE_ID,
      notificationEmailAddress: 'nexus-eng@amazon.com',
      selfMutate: true,
      createLegacyPipelineStage: false,
    });

    const versionSetStage = pipeline.versionSetStage;

    /**
     * Code review verification step
     * https://w.amazon.com/bin/view/CodeReviewVerification/
     */
    const versionSetApproval = versionSetStage.addApprovalWorkflow(VERSION_SET_APPROVAL_WORKFLOW);

    versionSetApproval.addStep(
      new CodeReviewVerificationApprovalWorkflowStep({
        name: 'Code review verification',
        authorizedGroups: [POSIX_GROUP],
        packageOwners: [POSIX_GROUP],
        notifyOnBypass: [TEAM_EMAIL],
      }),
    );

    /**
     * Gordian Knot to scan dependencies in VS.
     * https://w.amazon.com/bin/view/GordianKnot/PipelineApprovalStep/#HAddingusingCDK
     */
    versionSetApproval.addStep(
      new GordianKnotScannerApprovalWorkflowStep({
        name: 'Gordian Knot',
        scanProfileName: ScanProfile.ASSERT_IGNORE, // TODO: Change to ASSERT_LOW
        platform: VERSION_SET_PLATFORM,
      }),
    );

    /**
     * Awoke is a tool which helps answer questions about a pipeline:
     *    * What tests are currently failing and for how long?
     *    * What tests break frequently?
     * These questions are key for teams which want to keep their pipeline flowing.
     * It helps identify bottleneck tests and can inform decisions to improve tests.
     * It produces diagnostic reports automatically every time the approval workflow is run.
     * https://w.amazon.com/bin/view/Awoke/
     */
    versionSetApproval.addStep(
      new AwokeAnalysisApprovalWorkflowStep({
        name: 'Awoke Analysis',
      }),
    );

    /**
     * Trigger a pipeline build if any of these packages change.
     */
    ['NexusApplicationPipelineCDK'].map((pkg) => pipeline.addPackageToAutobuild(BrazilPackage.fromString(pkg)));

    PIPELINE_STAGE_CONFIGS.forEach((pipelineStageConfig) => {
      const pipelineStage = pipeline.addStage(pipelineStageConfig.pipelineStageName, {
        isProd: pipelineStageConfig.isProd,
      });

      const approvalSteps = new Array<ApprovalWorkflowStep>();

      pipelineStageConfig.computeEnvironments.forEach((computeEnvironment) => {
        const deploymentEnvironment = DeploymentEnvironmentFactory.fromAccountAndRegion(
          computeEnvironment.accountId,
          computeEnvironment.AWSRegion,
          `${PIPELINE_ID}`,
        );

        const vpcStack = this.createVPCStack(app, deploymentEnvironment, computeEnvironment);

        // Create SQS stack for mapping request queue and DLQ
        // This must be created before API handler to pass the queue URL
        const mappingRequestQueueStack = this.createSqsStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          vpcStack,
        );

        // Create deployment stack for api endpoint handler.
        // Pass the SQS queue for async mapping requests
        const apiEndpointLambdaStack = this.createAPIEndpointHandlerStack(
          app,
          computeEnvironment,
          deploymentEnvironment,
          pipelineStageConfig.isProd,
          approvalSteps,
          vpcStack,
          mappingRequestQueueStack,
        );

        const frameworksTable = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'Frameworks',
          'frameworkName',
          'version',
          [],
          [
            {
              indexName: 'FrameworkKeyIndex',
              partitionKey: {
                name: 'frameworkKey',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
            {
              indexName: 'StatusIndex',
              partitionKey: {
                name: 'status',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'frameworkName',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
          ],
        );

        const frameworkControlsTable = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'FrameworkControls',
          'frameworkKey',
          'controlKey',
          [],
          [
            {
              indexName: 'ControlKeyIndex',
              partitionKey: {
                name: 'controlKey',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
            {
              indexName: 'StatusIndex',
              partitionKey: {
                name: 'status',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'controlKey',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.KEYS_ONLY,
            },
          ],
        );

        const controlMappingsTable = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'ControlMappings',
          'controlKey',
          'mappedControlKey',
          [],
          [
            {
              indexName: 'MappingKeyIndex',
              partitionKey: {
                name: 'mappingKey',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
            {
              indexName: 'StatusIndex',
              partitionKey: {
                name: 'status',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'timestamp',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
            {
              indexName: 'WorkflowIndex',
              partitionKey: {
                name: 'mappingWorkflowKey',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'timestamp',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
            {
              indexName: 'ControlStatusIndex',
              partitionKey: {
                name: 'controlKey',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'status',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
          ],
        );

        const controlGuideIndex = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'ControlGuideIndex',
          'guideAttribute',
          'controlKey',
          [],
          [
            {
              indexName: 'ControlKeyIndex',
              partitionKey: {
                name: 'controlKey',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'guideAttribute',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.KEYS_ONLY,
            },
          ],
        );

        const mappingReviewsTable = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'MappingReviews',
          'mappingKey',
          'reviewKey',
          [],
          [
            {
              indexName: 'ReviewerIndex',
              partitionKey: {
                name: 'reviewerId',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'submittedAt',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
          ],
        );

        const mappingFeedbackTable = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'MappingFeedback',
          'mappingKey',
          'reviewerId',
          [],
          [
            {
              indexName: 'UserFeedbackIndex',
              partitionKey: {
                name: 'reviewerId',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'mappingKey',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
          ],
        );

        // MappingJobs table for async mapping workflow job tracking
        const mappingJobsTable = this.createDynamoDbStack(
          app,
          deploymentEnvironment,
          computeEnvironment,
          pipelineStageConfig.isProd,
          'MappingJobs',
          'job_id',
          '', // No sort key - single job_id primary key
          [],
          [
            {
              indexName: 'StatusIndex',
              partitionKey: {
                name: 'status',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'created_at',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
            {
              indexName: 'ControlKeyIndex',
              partitionKey: {
                name: 'control_key',
                type: dynamodb.AttributeType.STRING,
              },
              sortKey: {
                name: 'created_at',
                type: dynamodb.AttributeType.STRING,
              },
              projectionType: ProjectionType.ALL,
            },
          ],
        );

        const appConfigStack = new AppConfigStack(
          app,
          `AppConfig-${this.generateComputeEnvironmentIdentifier(computeEnvironment)}`,
          {
            serviceName: SERVICE_NAME,
            env: deploymentEnvironment,
            stage: computeEnvironment.stage,
            region: computeEnvironment.region,
            awsRegion: computeEnvironment.AWSRegion,
            computeEnvironmentIdentifier: this.generateComputeEnvironmentIdentifier(computeEnvironment),
          },
        );

        const dashboardStack = new DashboardStack(
          app,
          `Dashboard-${this.generateComputeEnvironmentIdentifier(computeEnvironment)}`,
          {
            env: deploymentEnvironment,
            stage: computeEnvironment.stage,
            awsRegion: computeEnvironment.AWSRegion,
            isProd: pipelineStageConfig.isProd,
            alarms: [],
            metrics: [],
          },
        );

        const deploymentGroupName = `${computeEnvironment.accountId}-${computeEnvironment.stage}`;
        pipelineStage.addDeploymentGroup({
          name: deploymentGroupName,
          stacks: [
            appConfigStack,
            vpcStack,
            mappingRequestQueueStack,
            apiEndpointLambdaStack,
            frameworksTable,
            frameworkControlsTable,
            controlMappingsTable,
            controlGuideIndex,
            mappingReviewsTable,
            mappingFeedbackTable,
            mappingJobsTable,
            dashboardStack,
          ],
        });
        const approvalWorkflow = pipelineStage.addApprovalWorkflow(
          `Approval workflow ${pipelineStageConfig.pipelineStageName}`,
        );
        approvalSteps.forEach((step) => {
          approvalWorkflow.addStep(step);
        });
      });
    });
  }

  /**
   * Helper method to generate compute environment identifier.
   *
   * @param computeEnvironment
   * @private
   */
  private generateComputeEnvironmentIdentifier(computeEnvironment: ComputeEnvironment) {
    return `${computeEnvironment.accountId}-${computeEnvironment.AWSRegion}-${computeEnvironment.stage}`;
  }

  private createVPCStack(
    app: App,
    deploymentEnvironment: DeploymentEnvironment,
    computeEnvironment: ComputeEnvironment,
  ) {
    return new VpcDeploymentStack(
      app,
      `${SERVICE_NAME}VPC-${this.generateComputeEnvironmentIdentifier(computeEnvironment)}`,
      {
        env: deploymentEnvironment,
        stage: computeEnvironment.stage,
        isProd: false,
        maxAzs: 1,
      },
    );
  }

  /**
   * Helper method to create DynamoDB stack.
   *
   * @param app
   * @param deploymentEnvironment
   * @param computeEnvironment
   * @param isProd
   * @param tableName
   * @param partitionKey
   * @param sortKey
   * @param arns
   * @param globalSecondaryIndexes
   * @private
   */
  private createDynamoDbStack(
    app: App,
    deploymentEnvironment: DeploymentEnvironment,
    computeEnvironment: ComputeEnvironment,
    isProd: boolean,
    tableName: string,
    partitionKey: string,
    sortKey: string,
    arns?: string[],
    globalSecondaryIndexes?: dynamodb.GlobalSecondaryIndexProps[],
  ) {
    return new DynamodbStack(
      app,
      `DynamoDB-${tableName}-${this.generateComputeEnvironmentIdentifier(computeEnvironment)}`,
      {
        env: deploymentEnvironment,
        stage: computeEnvironment.stage,
        region: computeEnvironment.region,
        awsRegion: computeEnvironment.AWSRegion,
        isProd: isProd,
        tableName: tableName,
        partitionKey: partitionKey,
        sortKey: sortKey,
        accountId: computeEnvironment.accountId,
        arns: arns,
        globalSecondaryIndexes: globalSecondaryIndexes,
      },
    );
  }

  private createAPIEndpointHandlerStack(
    app: App,
    computeEnvironment: ComputeEnvironment,
    deploymentEnvironment: DeploymentEnvironment,
    isProd: boolean,
    approvalSteps: Array<ApprovalWorkflowStep>,
    vpcStack: VpcDeploymentStack,
    mappingRequestQueueStack?: MappingRequestQueueStack,
  ) {
    const apiEndpointHandlerLambdaStackName = `APIEndpointHandler-${this.generateComputeEnvironmentIdentifier(computeEnvironment)}`;

    const apiEndpointLambdaStack = new ApiEndpointHandlerLambdaStack(app, apiEndpointHandlerLambdaStackName, {
      env: deploymentEnvironment,
      stage: computeEnvironment.stage,
      region: computeEnvironment.region,
      awsRegion: computeEnvironment.AWSRegion,
      isProd: isProd,
      vpc: vpcStack.vpc,
      mappingRequestQueue: mappingRequestQueueStack?.mappingRequestQueue,
    });

    return apiEndpointLambdaStack;
  }

  /**
   * Helper method to create SQS stack for mapping request queue and DLQ.
   *
   * @param app
   * @param deploymentEnvironment
   * @param computeEnvironment
   * @param isProd
   * @param vpcStack
   * @param stateMachineArn
   * @private
   */
  private createSqsStack(
    app: App,
    deploymentEnvironment: DeploymentEnvironment,
    computeEnvironment: ComputeEnvironment,
    isProd: boolean,
    vpcStack: VpcDeploymentStack,
    stateMachineArn?: string,
  ) {
    return new MappingRequestQueueStack(
      app,
      `MappingRequestQueue-${this.generateComputeEnvironmentIdentifier(computeEnvironment)}`,
      {
        env: deploymentEnvironment,
        stage: computeEnvironment.stage,
        region: computeEnvironment.region,
        awsRegion: computeEnvironment.AWSRegion,
        isProd: isProd,
        accountId: computeEnvironment.accountId,
        vpc: vpcStack.vpc,
        stateMachineArn: stateMachineArn,
      },
    );
  }
}
