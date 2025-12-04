import * as certmgr from 'aws-cdk-lib/aws-certificatemanager';
import { Construct } from 'constructs';
import { CertificateValidation } from 'aws-cdk-lib/aws-certificatemanager';

export function generateSSLCertificate(scope: Construct, name: string, domainName: string) {
  const SSLCertificate = new certmgr.Certificate(scope, name, {
    domainName: domainName,
    // TODO: Obtain hosted zone and pass it as argument below. https://tiny.amazon.com/lzyfnq7q/codeamazpackAwsgblobb197apps
    validation: CertificateValidation.fromDns(),
  });

  return SSLCertificate;
}
