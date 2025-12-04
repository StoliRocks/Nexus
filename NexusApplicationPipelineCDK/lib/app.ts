import { App } from 'aws-cdk-lib';
import { PipelineInfrastructure } from './pipeline/pipeline';

// Set up your CDK App
const app = new App();

new PipelineInfrastructure(app);
