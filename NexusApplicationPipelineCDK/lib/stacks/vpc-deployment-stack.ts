import { DeploymentStack, SoftwareType } from '@amzn/pipelines';
import { Construct } from 'constructs';
import { VpcStackProps } from '../props/VpcStackProps';
import { SERVICE_NAME } from '../utils/constants';
import { InterfaceVpcEndpointAwsService, SubnetType, Vpc } from 'aws-cdk-lib/aws-ec2';
import { CustomIpAddressAllocator } from '../utils/custom-ip-address-allocator';

export class VpcDeploymentStack extends DeploymentStack {
  public readonly vpc: Vpc;

  constructor(scope: Construct, id: string, props: VpcStackProps) {
    super(scope, id, {
      env: props.env,
      description: `${SERVICE_NAME} VPC Stack`,
      stackName: `${SERVICE_NAME}VPC-${props.stage}`,
      softwareType: SoftwareType.INFRASTRUCTURE,
    });

    if (!props.isProd) {
      this.vpc = new Vpc(this, `${SERVICE_NAME}-VPC-${props.stage}`, {
        // ipAddresses: new CustomIpAddressAllocator(),
        // ToDo: read max AZ from props. example: maxAzs: this.availabilityZones.length,
        maxAzs: props.maxAzs,
        vpcName: `${SERVICE_NAME}-VPC-${props.stage}`,
        subnetConfiguration: [
          {
            cidrMask: 24,
            name: 'Public',
            subnetType: SubnetType.PUBLIC,
          },
          {
            cidrMask: 24,
            name: 'Private',
            subnetType: SubnetType.PRIVATE_WITH_EGRESS, // Private subnet with NAT Gateway
          },
        ],
      });
    } else {
      this.vpc = new Vpc(this, `${SERVICE_NAME}-VPC-${props.stage}`, {
        ipAddresses: new CustomIpAddressAllocator(),
        maxAzs: this.availabilityZones.length,
        vpcName: `${SERVICE_NAME}-VPC-${props.stage}`,
        subnetConfiguration: [
          {
            cidrMask: 24,
            name: 'Public',
            subnetType: SubnetType.PUBLIC,
          },
          {
            cidrMask: 24,
            name: 'Private',
            subnetType: SubnetType.PRIVATE_ISOLATED, // Private subnet with NAT Gateway
          },
        ],
      });

      // TODO: Add more endpoints before deploying to Prod
      // Add VPC Endpoints for AWS services
      this.vpc.addInterfaceEndpoint('StepFunctions', {
        service: InterfaceVpcEndpointAwsService.STEP_FUNCTIONS,
      });

      this.vpc.addInterfaceEndpoint('SQS', {
        service: InterfaceVpcEndpointAwsService.SQS,
      });
    }
  }
}
