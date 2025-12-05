type PipelineStage = 'beta' | 'gamma' | 'prod';

export type ComputeEnvironment = {
  region: string;
  stage: string;
  AWSRegion: string;
  accountId: string;
};

type PipelineStageConfig = {
  pipelineStageName: string;
  stage: PipelineStage;
  isProd: boolean;
  computeEnvironments: ComputeEnvironment[];
};

export const PIPELINE_STAGE_CONFIGS: PipelineStageConfig[] = [
  {
    pipelineStageName: 'Beta',
    stage: 'beta',
    isProd: false,
    computeEnvironments: [
      {
        region: 'NA',
        stage: 'beta',
        AWSRegion: 'us-east-1',
        accountId: '909139952351',
      },
    ],
  },
  {
    pipelineStageName: 'Gamma',
    stage: 'gamma',
    isProd: false,
    computeEnvironments: [
      {
        region: 'NA',
        stage: 'gamma',
        AWSRegion: 'us-east-1',
        accountId: '098092129359',
      },
    ],
  },
  {
    pipelineStageName: 'Prod',
    stage: 'prod',
    isProd: true,
    computeEnvironments: [
      {
        region: 'NA',
        stage: 'prod',
        AWSRegion: 'us-east-1',
        accountId: '305345571965',
      },
    ],
  },
];
