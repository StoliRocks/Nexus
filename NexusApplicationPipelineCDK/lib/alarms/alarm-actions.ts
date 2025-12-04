import { Severity, SIMTicketAlarmAction } from '@amzn/sim-ticket-cdk-constructs';

export interface CTI {
  category: string;
  type: string;
  item: string;
  group: string;
}

const NEXUS_CTI: CTI = {
  category: 'Global Services Security',
  type: 'Innovation in Science-Engineering',
  item: 'Nexus',
  group: 'nexus-builders',
};

function createSIMAlarmAction(cti: CTI, severity: Severity): SIMTicketAlarmAction {
  return new SIMTicketAlarmAction({
    ctiCategory: cti.category,
    ctiType: cti.type,
    ctiItem: cti.item,
    group: cti.group,
    severity: severity,
  });
}

export function createNexusSIMAlarmAction(severity: Severity): SIMTicketAlarmAction {
  return createSIMAlarmAction(NEXUS_CTI, severity);
}
