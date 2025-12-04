const GSS_DEV_DOMAIN_PREFIX = 'gss.aws.dev';
const TEAM_DOMAIN_PREFIX = `science-engineering.${GSS_DEV_DOMAIN_PREFIX}`;
const NEXUS_SUBDOMAIN_PREFIX = `nexus.${TEAM_DOMAIN_PREFIX}`;

export function generateDomainName(resource: string, stage: string, region: string) {
  const domainStage = stage === 'prod' ? '' : `${stage}.`;
  const domainRegion = region === 'NA' ? '' : `${region.toLowerCase()}.`;
  return `${resource}.${domainStage}${domainRegion}${NEXUS_SUBDOMAIN_PREFIX}`;
}
