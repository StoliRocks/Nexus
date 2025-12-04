import { AllocateCidrRequest, IpAddresses, SubnetIpamOptions, VpcIpamOptions } from 'aws-cdk-lib/aws-ec2';
import { VPC_SUBNET_IP_ADDRESS } from './constants';

const CIDRS_BY_SUBNET_NAME: Record<string, string[]> = {
  Public: [
    // Initial subnets - 8,192 ips per subnet
    '10.0.0.0/19', // PublicSubnet1
    '10.0.32.0/19', // PublicSubnet2
    '10.0.64.0/19', // PublicSubnet3
    // Additional subnets - 1,024 ips per subnet
    '10.0.192.0/22', // PublicSubnet4
    '10.0.196.0/22', // PublicSubnet5
    '10.0.200.0/22', // PublicSubnet6
    '10.0.204.0/22', // PublicSubnet7
    '10.0.208.0/22', // PublicSubnet8
    '10.0.212.0/22', // PublicSubnet9
    '10.0.216.0/22', // PublicSubnet10
  ],
  Private: [
    // Initial subnets - 8,192 ips per subnet
    '10.0.96.0/19', // PrivateSubnet1
    '10.0.128.0/19', // PrivateSubnet2
    '10.0.160.0/19', // PrivateSubnet3
    // Additional subnets - 1,024 ips per subnet
    '10.0.220.0/22', // PrivateSubnet4
    '10.0.224.0/22', // PrivateSubnet5
    '10.0.228.0/22', // PrivateSubnet6
    '10.0.232.0/22', // PrivateSubnet7
    '10.0.236.0/22', // PrivateSubnet8
    '10.0.240.0/22', // PrivateSubnet9
    '10.0.244.0/22', // PrivateSubnet10
  ],
};

export class CustomIpAddressAllocator implements IpAddresses {
  allocateVpcCidr(): VpcIpamOptions {
    return IpAddresses.cidr(VPC_SUBNET_IP_ADDRESS).allocateVpcCidr();
  }

  allocateSubnetsCidr(input: AllocateCidrRequest): SubnetIpamOptions {
    const subnetIndex: Record<string, number> = {
      Public: 0,
      Private: 0,
    };
    const allocatedSubnets = input.requestedSubnets.map((subnet) => {
      const type = subnet.configuration.subnetType;
      const cidrCandidates = CIDRS_BY_SUBNET_NAME[type];
      const cidr = cidrCandidates[subnetIndex[type]];
      subnetIndex[type] += 1;
      return {
        cidr,
      };
    });
    return {
      allocatedSubnets,
    };
  }
}
