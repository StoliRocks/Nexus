import {
  Application,
  ConfigurationContent,
  DeploymentStrategy,
  Environment,
  HostedConfiguration,
  JsonSchemaValidator,
  RolloutStrategy,
} from 'aws-cdk-lib/aws-appconfig';
import { Construct } from 'constructs';
import { DeploymentStack, SoftwareType } from '@amzn/pipelines';
import { AwsAppConfigProps } from '../../props/AwsAppConfigProps';

const APP_CONFIG_STACK_NAME = `AwsAppConfig`;

const INGESTION_PIPELINE_CONFIG_SCHEMA = './lib/config/ingestion/ingestion_pipeline_config_schema.json';
const APP_CONFIG_INGESTION_PIPELINE_FILE_MAP: { [key: string]: string } = {
  'alpha-NA': './lib/config/ingestion/alpha_ingestion_pipeline_config.json',
  'beta-NA': './lib/config/ingestion/beta_ingestion_pipeline_config.json',
  'beta-EU': './lib/config/ingestion/beta_ingestion_pipeline_config.json',
  'beta-FE': './lib/config/ingestion/beta_ingestion_pipeline_config.json',
};

const QUERY_PIPELINE_CONFIG_SCHEMA = './lib/config/query/query_pipeline_config_schema.json';
const APP_CONFIG_QUERY_PIPELINE_FILE_MAP: { [key: string]: string } = {
  'alpha-NA': './lib/config/query/alpha_query_pipeline_config.json',
  'beta-NA': './lib/config/query/beta_query_pipeline_config.json',
  'beta-EU': './lib/config/query/beta_query_pipeline_config.json',
  'beta-FE': './lib/config/query/beta_query_pipeline_config.json',
};

interface DeploymentStrategyConfigProps {
  readonly name: string;
  readonly deploymentDurationInMinutes: number;
  readonly finalBakeTimeInMinutes: number;
  readonly growthFactor: number;
  readonly growthType: string;
  readonly replicateTo: string;
}

interface ConfigProfileProps {
  readonly schemaFilePath: string;
  readonly configFilePath: string;
  readonly configName: string;
  readonly deploymentStrategyConfigProps: DeploymentStrategyConfigProps;
}

/**
 * Creates deployment stack for AppConfig. The stack can be created using following steps.
 * https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/AWS_AppConfig.html
 *
 * 1. Create an application
 * 2. Create an environment to deploy in.
 * 3. Create configuration profile for each type of AppConfig.
 * 4. Create a deployment strategy for each profile.
 * 5. Deploy the AppConfig.
 */
export class AppConfigStack extends DeploymentStack {
  constructor(scope: Construct, id: string, props: AwsAppConfigProps) {
    super(scope, id, {
      env: props.env,
      softwareType: SoftwareType.INFRASTRUCTURE,
    });

    // Create an AppConfig application
    const appConfigApplication = new Application(this, `${props.serviceName}-AppConfig-Application`, {
      applicationName: `${props.serviceName}-${props.stage}-${props.region}`,
      description: `This is the application for ${props.stage} in ${props.region}.`,
    });

    // Define an environment to deploy to
    const appConfigEnvironment = new Environment(this, id, {
      environmentName: `${props.serviceName}-AppConfig-Environment`,
      application: appConfigApplication,
    });

    this.getAppConfigProfileProps(props.serviceName, props.stage, props.region).forEach((profile) => {
      appConfigEnvironment.addDeployment(
        new HostedConfiguration(this, profile.configName, {
          name: profile.configName,
          application: appConfigApplication,
          content: ConfigurationContent.fromFile(profile.configFilePath),
          deploymentStrategy: this.createDeploymentStrategy(`${APP_CONFIG_STACK_NAME}-${profile.configName}`),
          validators: [JsonSchemaValidator.fromFile(`${profile.schemaFilePath}`)],
        }),
      );
    });
  }

  /**
   * Create deployment strategy
   *
   * @param configProfileName
   * @private
   */
  private createDeploymentStrategy(configProfileName: string): DeploymentStrategy {
    return new DeploymentStrategy(this, `${configProfileName}-AppConfig-Deployment-Strategy`, {
      rolloutStrategy: RolloutStrategy.ALL_AT_ONCE,
    });
  }

  /**
   * Create profile for each AppConfig.
   *
   * @param serviceName
   * @param stage
   * @param region
   * @private
   */
  private getAppConfigProfileProps(serviceName: string, stage: string, region: string): ConfigProfileProps[] {
    return [
      {
        schemaFilePath: INGESTION_PIPELINE_CONFIG_SCHEMA,
        configName: `${serviceName}-IngestionPipelineConfig`,
        configFilePath:
          APP_CONFIG_INGESTION_PIPELINE_FILE_MAP[`${stage}-${region}`] ||
          APP_CONFIG_INGESTION_PIPELINE_FILE_MAP[`beta-NA`],
        deploymentStrategyConfigProps: {
          name: 'LinearDeployment',
          deploymentDurationInMinutes: 30,
          finalBakeTimeInMinutes: 30,
          growthFactor: 20,
          growthType: 'LINEAR',
          replicateTo: 'NONE',
        },
      },
      {
        schemaFilePath: QUERY_PIPELINE_CONFIG_SCHEMA,
        configName: `${serviceName}-QueryPipelineConfig`,
        configFilePath:
          APP_CONFIG_QUERY_PIPELINE_FILE_MAP[`${stage}-${region}`] || APP_CONFIG_QUERY_PIPELINE_FILE_MAP[`beta-NA`],
        deploymentStrategyConfigProps: {
          name: 'LinearDeployment',
          deploymentDurationInMinutes: 30,
          finalBakeTimeInMinutes: 30,
          growthFactor: 20,
          growthType: 'LINEAR',
          replicateTo: 'NONE',
        },
      },
    ];
  }
}
