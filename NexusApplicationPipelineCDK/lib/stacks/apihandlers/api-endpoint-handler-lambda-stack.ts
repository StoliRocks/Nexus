import {
  DeploymentEnvironment,
  DeploymentStack,
  SoftwareType,
} from '@amzn/pipelines';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Alias } from 'aws-cdk-lib/aws-lambda';
import { Alarm } from 'aws-cdk-lib/aws-cloudwatch';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import {
  AccessLogField,
  AccessLogFormat,
  CfnAccount,
  LogGroupLogDestination,
  TokenAuthorizer,
} from 'aws-cdk-lib/aws-apigateway';
import { LogGroup } from 'aws-cdk-lib/aws-logs';
import { Duration, Fn } from 'aws-cdk-lib';
import { DEFAULT_BRAZIL_PYTHON_RUNTIME } from '../../runtime/runtime';
import { DEFAULT_LOG_GROUP_RETENTION_PERIOD, NEXUS_REST_API_NAME } from '../../utils/constants';
import { CfnWebACL } from 'aws-cdk-lib/aws-wafv2';
import { generateDomainName } from '../../utils/domain';
import { ILambdaDeploymentConfig, LambdaDeploymentConfig, LambdaDeploymentGroup } from 'aws-cdk-lib/aws-codedeploy';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';
import { Effect, ManagedPolicy, PolicyStatement, Role, ServicePrincipal } from 'aws-cdk-lib/aws-iam';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { LambdaMetricAlarms } from '../../alarms/lambda-metric-alarms';
import { ApiEndpointAlarms } from '../../alarms/api-endpoint-alarms';
import { FrameworkManagementHandler } from './framework-management-handler';
import { ControlManagementHandler } from './control-management-handler';
import { MappingManagementHandler } from './mapping-management-handler';
import { MappingReviewManagementHandler } from './mapping-review-management-handler';
import { MappingFeedbackManagementHandler } from './mapping-feedback-management-handler';
import { AsyncMappingHandler } from './async-mapping-handler';

const NEXUS_CUSTOM_AUTHORIZER_NAME = 'NexusLambdaAuthorizer';

export class ApiEndpointHandlerLambdaStack extends DeploymentStack {
  private readonly tokenAuthorizer: TokenAuthorizer;
  private readonly stage: string;
  private readonly apiEndpoints: apigateway.RestApi;
  private readonly frameworkHandler: FrameworkManagementHandler;
  private readonly controlHandler: ControlManagementHandler;
  private readonly mappingHandler: MappingManagementHandler;
  private readonly mappingReviewHandler: MappingReviewManagementHandler;
  private readonly mappingFeedbackHandler: MappingFeedbackManagementHandler;
  private readonly asyncMappingHandler: AsyncMappingHandler;

  // Lambda aliases for deployment management
  private readonly frameworkHandlerAlias: Alias;
  private readonly controlHandlerAlias: Alias;
  private readonly mappingHandlerAlias: Alias;
  private readonly mappingReviewHandlerAlias: Alias;
  private readonly mappingFeedbackHandlerAlias: Alias;
  private readonly asyncHandlerAlias: Alias;
  private readonly statusHandlerAlias: Alias;

  // Pipelines will inject a boolean value into a stack parameter that
  // can be examined to determine if a deployment is a rollback. This
  // enables one to deploy more aggressively during a rollback [e.g.,
  // to ignore alarms or disable incremental deployment]. To do so
  // require one to select a value for these settings at deploy-time,
  // by using a CloudFormation conditional expression.
  private readonly ifRollback = <T extends string>(then: T, otherwise: T): T =>
    Fn.conditionIf(this.pipelinesRollbackCondition.logicalId, then, otherwise).toString() as T;

  constructor(scope: Construct, id: string, props: APIEndpointHandlerStackProps) {
    super(scope, id, {
      env: props.env,
      softwareType: SoftwareType.LONG_RUNNING_SERVICE,
    });

    this.stage = props.stage;

    // Custom authorizer: Create reference to the existing authorizer Lambda function
    const authorizerFunction = createLambdaFunctionInstance(
      this,
      `${NEXUS_CUSTOM_AUTHORIZER_NAME}`,
      'APIAuthorizer',
      `${NEXUS_CUSTOM_AUTHORIZER_NAME}`,
      '1.0',
      'nexus_lambda_authorizer.handler.lambda_handler',
      Duration.minutes(15),
      props.vpc,
    );

    // Create the authorizer configuration
    this.tokenAuthorizer = new apigateway.TokenAuthorizer(this, 'NexusApiAuthorizer', {
      handler: authorizerFunction,
      identitySource: apigateway.IdentitySource.header('Authorization'),
      resultsCacheTtl: Duration.minutes(5),
    });

    // Create all management handlers
    this.frameworkHandler = new FrameworkManagementHandler(this, props);
    this.controlHandler = new ControlManagementHandler(this, props);
    this.mappingHandler = new MappingManagementHandler(this, props);
    this.mappingReviewHandler = new MappingReviewManagementHandler(this, props);
    this.mappingFeedbackHandler = new MappingFeedbackManagementHandler(this, props);
    this.asyncMappingHandler = new AsyncMappingHandler(this, 'AsyncMappingHandler', {
      ...props,
      mappingRequestQueue: props.mappingRequestQueue,
    });

    // Add CloudWatch permissions to all handlers
    this.addCloudWatchPermissions(this.frameworkHandler.frameworkHandler);
    this.addCloudWatchPermissions(this.controlHandler.controlHandler);
    this.addCloudWatchPermissions(this.mappingHandler.mappingHandler);
    this.addCloudWatchPermissions(this.mappingReviewHandler.mappingReviewHandler);
    this.addCloudWatchPermissions(this.mappingFeedbackHandler.mappingFeedbackHandler);
    this.addCloudWatchPermissions(this.asyncMappingHandler.asyncHandler);
    this.addCloudWatchPermissions(this.asyncMappingHandler.statusHandler);

    // API gateway REST API resource
    this.apiEndpoints = this.setupRESTAPI(props);

    // Setup API resources for each handler
    const { frameworkVersionResource, v1Resource } = this.frameworkHandler.setupFrameworkAPIResources(
      this.apiEndpoints,
      this.tokenAuthorizer,
    );
    this.controlHandler.setupControlAPIResources(frameworkVersionResource, this.tokenAuthorizer);
    const { mappingsResource, mappingIdResource } = this.mappingHandler.setupMappingAPIResources(
      v1Resource,
      this.tokenAuthorizer,
    );
    this.mappingReviewHandler.setupMappingReviewAPIResources(mappingIdResource, this.tokenAuthorizer);
    this.mappingFeedbackHandler.setupMappingFeedbackAPIResources(mappingIdResource, this.tokenAuthorizer);
    this.asyncMappingHandler.setupAsyncMappingAPIResources(mappingsResource, mappingIdResource, this.tokenAuthorizer);

    // Grant custom authorizer permission to call API endpoint.
    authorizerFunction.addPermission('ApiGatewayInvokeAuthorizer', {
      principal: new ServicePrincipal('apigateway.amazonaws.com'),
      action: 'lambda:InvokeFunction',
      sourceArn: this.apiEndpoints.arnForExecuteApi('*'),
    });

    // Create lambda aliases for all handlers
    this.frameworkHandlerAlias = this.createAlias('FrameworkHandler', this.frameworkHandler.frameworkHandler);
    this.controlHandlerAlias = this.createAlias('ControlHandler', this.controlHandler.controlHandler);
    this.mappingHandlerAlias = this.createAlias('MappingHandler', this.mappingHandler.mappingHandler);
    this.mappingReviewHandlerAlias = this.createAlias('MappingReviewHandler', this.mappingReviewHandler.mappingReviewHandler);
    this.mappingFeedbackHandlerAlias = this.createAlias('MappingFeedbackHandler', this.mappingFeedbackHandler.mappingFeedbackHandler);
    this.asyncHandlerAlias = this.createAlias('AsyncHandler', this.asyncMappingHandler.asyncHandler);
    this.statusHandlerAlias = this.createAlias('StatusHandler', this.asyncMappingHandler.statusHandler);

    // Create alarms for API endpoints
    new ApiEndpointAlarms(this, props.env, props.stage, props.awsRegion);

    // Framework handler alarms
    const frameworkAlarms = new LambdaMetricAlarms(
      this,
      this.frameworkHandler.frameworkHandler,
      this.frameworkHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Control handler alarms
    const controlAlarms = new LambdaMetricAlarms(
      this,
      this.controlHandler.controlHandler,
      this.controlHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Mapping handler alarms
    const mappingAlarms = new LambdaMetricAlarms(
      this,
      this.mappingHandler.mappingHandler,
      this.mappingHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Mapping review handler alarms
    const mappingReviewAlarms = new LambdaMetricAlarms(
      this,
      this.mappingReviewHandler.mappingReviewHandler,
      this.mappingReviewHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Mapping feedback handler alarms
    const mappingFeedbackAlarms = new LambdaMetricAlarms(
      this,
      this.mappingFeedbackHandler.mappingFeedbackHandler,
      this.mappingFeedbackHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Async handler alarms
    const asyncAlarms = new LambdaMetricAlarms(
      this,
      this.asyncMappingHandler.asyncHandler,
      this.asyncHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Status handler alarms
    const statusAlarms = new LambdaMetricAlarms(
      this,
      this.asyncMappingHandler.statusHandler,
      this.statusHandlerAlias,
      props.isProd,
      props.stage,
      props.awsRegion,
    );

    // Configure autoscaling for all handlers
    this.configureAutoscaling(this.frameworkHandlerAlias);
    this.configureAutoscaling(this.controlHandlerAlias);
    this.configureAutoscaling(this.mappingHandlerAlias);
    this.configureAutoscaling(this.mappingReviewHandlerAlias);
    this.configureAutoscaling(this.mappingFeedbackHandlerAlias);
    this.configureAutoscaling(this.asyncHandlerAlias);
    this.configureAutoscaling(this.statusHandlerAlias);

    // Gradual deployment only for prod stage. For other stages, deployment will be one-shot.
    if (props.isProd) {
      this.createDeploymentGroup('FrameworkHandler', this.frameworkHandlerAlias, [...frameworkAlarms.getSev2Alarms()], props.isProd);
      this.createDeploymentGroup('ControlHandler', this.controlHandlerAlias, [...controlAlarms.getSev2Alarms()], props.isProd);
      this.createDeploymentGroup('MappingHandler', this.mappingHandlerAlias, [...mappingAlarms.getSev2Alarms()], props.isProd);
      this.createDeploymentGroup('MappingReviewHandler', this.mappingReviewHandlerAlias, [...mappingReviewAlarms.getSev2Alarms()], props.isProd);
      this.createDeploymentGroup('MappingFeedbackHandler', this.mappingFeedbackHandlerAlias, [...mappingFeedbackAlarms.getSev2Alarms()], props.isProd);
      this.createDeploymentGroup('AsyncHandler', this.asyncHandlerAlias, [...asyncAlarms.getSev2Alarms()], props.isProd);
      this.createDeploymentGroup('StatusHandler', this.statusHandlerAlias, [...statusAlarms.getSev2Alarms()], props.isProd);
    }

  }

  /**
   * Add CloudWatch permissions to a lambda function.
   *
   * @private
   * @param lambdaFunction
   */
  private addCloudWatchPermissions(lambdaFunction: lambda.Function) {
    lambdaFunction.addToRolePolicy(
      new PolicyStatement({
        actions: ['cloudwatch:PutMetricData', 'logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
        effect: Effect.ALLOW,
        resources: ['*'],
      }),
    );
  }

  /**
   * Autoscale lambda instances to handle more requests.
   *
   * @private
   * @param alias
   */
  private configureAutoscaling(alias: Alias) {
    const autoScaling = alias.addAutoScaling({ maxCapacity: 10 });
    autoScaling.scaleOnUtilization({ utilizationTarget: 0.5 });
  }

  /**
   * Create alias for lambda, needed for autoscaling.
   *
   * @private
   * @param name
   * @param lambdaFunction
   */
  private createAlias(name: string, lambdaFunction: lambda.Function): Alias {
    return new Alias(this, `${name}Alias`, {
      aliasName: 'live',
      version: lambdaFunction.currentVersion,
    });
  }

  /**
   * Create deployment group for a lambda handler.
   *
   * @private
   * @param name
   * @param alias
   * @param alarms
   * @param isProd
   */
  private createDeploymentGroup(name: string, alias: Alias, alarms: Alarm[], isProd: boolean) {
    new LambdaDeploymentGroup(this, `${name}DeploymentGroup`, {
      alias: alias,
      deploymentConfig: this.createDeploymentConfig(isProd),
      alarms: alarms,
    });
  }

  /**
   * Setup REST API endpoints.
   *
   * @private
   * @param prop
   */
  private setupRESTAPI(prop: APIEndpointHandlerStackProps): apigateway.RestApi {
    const logGroup = new LogGroup(this, 'NexusRESTAPIEndpointLogGroup', {
      retention: DEFAULT_LOG_GROUP_RETENTION_PERIOD,
    });
    const domainName = generateDomainName('api', prop.stage, prop.region);

    const webACL = this.configureWebACL();

    const api = new apigateway.RestApi(this, NEXUS_REST_API_NAME, {
      restApiName: NEXUS_REST_API_NAME,
      description: 'Nexus API Gateway for framework, control, and mapping management',
      cloudWatchRole: true,
      defaultMethodOptions: {
        authorizer: this.tokenAuthorizer,
        authorizationType: apigateway.AuthorizationType.CUSTOM,
      },
      deployOptions: {
        accessLogDestination: new LogGroupLogDestination(logGroup),
        accessLogFormat: this.getAccessLogFormat(),
        dataTraceEnabled: !prop.isProd,
        tracingEnabled: true,
        metricsEnabled: true,
      },
      // domainName: {
      //   domainName: domainName,
      //   certificate: generateSSLCertificate(this, `Certificate.${domainName}`, domainName),
      //   securityPolicy: SecurityPolicy.TLS_1_2,
      // },
    });

    // Grant API gateway permissions to push logs to Cloudwatch. Enabling logs is done
    // at the account level so we dont need to attach the CfnAccount construct to anything.
    const apiGatewayLoggingRole = new Role(this, 'APIEndpointLoggingRole', {
      assumedBy: new ServicePrincipal('apigateway.amazonaws.com'),
      managedPolicies: [ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonAPIGatewayPushToCloudWatchLogs')],
    });
    const apiGatewayAccount = new CfnAccount(this, 'Account', {
      cloudWatchRoleArn: apiGatewayLoggingRole.roleArn,
    });

    return api;
  }

  /**
   * WebACL is needed when setting up a domain for API endpoints.
   * @private
   */
  private configureWebACL() {
    // TODO: Add Web Access control list (WebACL) https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html
    const webACL = new CfnWebACL(this, 'NexusWebACL', {
      scope: 'REGIONAL',
      visibilityConfig: {
        cloudWatchMetricsEnabled: true,
        metricName: 'NexusRESTAPIWebACL',
        sampledRequestsEnabled: false,
      },
      defaultAction: {
        allow: {},
      },
    });

    return webACL;
  }

  /**
   * Generate AccessLogFormat for logging REST API activities.
   * @private
   */
  private getAccessLogFormat(): AccessLogFormat {
    const requester = [
      AccessLogField.contextCallerAccountId(),
      AccessLogField.contextIdentityCaller(),
      AccessLogField.contextIdentityUser(),
    ].join(' ');
    const userAgent = AccessLogField.contextIdentityUserAgent();
    const requestTime = AccessLogField.contextRequestTime();
    const request = [
      AccessLogField.contextHttpMethod(),
      AccessLogField.contextResourcePath(),
      AccessLogField.contextProtocol(),
    ].join(' ');
    const status = [
      AccessLogField.contextStatus(),
      AccessLogField.contextResponseLength(),
      AccessLogField.contextRequestId(),
    ].join(' ');

    return AccessLogFormat.custom(`${requester} [${userAgent}] [${requestTime}] "${request}" ${status}`);
  }

  private createDeploymentConfig(isProd: boolean): ILambdaDeploymentConfig {
    const deploymentConfiguration = isProd
      ? LambdaDeploymentConfig.CANARY_10PERCENT_5MINUTES
      : LambdaDeploymentConfig.ALL_AT_ONCE;
    const rollbackDeploymentConfiguration = LambdaDeploymentConfig.ALL_AT_ONCE;

    // Support in CDK for CloudFormation conditional expressions is limited to simple
    // types. Thus, we condition the value of each attribute of a single shape,
    // instead of conditionally returning one of two shapes.
    // See https://github.com/aws/aws-cdk/issues/8396
    return {
      deploymentConfigName: this.ifRollback(
        rollbackDeploymentConfiguration.deploymentConfigName,
        deploymentConfiguration.deploymentConfigName,
      ),
      deploymentConfigArn: this.ifRollback(
        rollbackDeploymentConfiguration.deploymentConfigArn,
        deploymentConfiguration.deploymentConfigArn,
      ),
    };
  }
}
