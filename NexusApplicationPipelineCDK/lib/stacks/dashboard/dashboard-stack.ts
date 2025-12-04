import { DeploymentStack, SoftwareType } from '@amzn/pipelines';
import { Construct } from 'constructs';
import { AlarmWidget, GraphWidget, TextWidget } from 'aws-cdk-lib/aws-cloudwatch';
import { Duration } from 'aws-cdk-lib';
import { RUNBOOK_PATH_PREFIX, SERVICE_NAME } from '../../utils/constants';
import {
  AccountSpecificDedupe,
  AmazonAlarmFactoryDefaults,
  AmazonMetricFactoryDefaults,
  AmazonMonitoringFacade,
} from '@amzn/monitoring';
import { DashboardStackProps } from '../../props/DashboardStackProps';

export class DashboardStack extends DeploymentStack {
  constructor(scope: Construct, id: string, props: DashboardStackProps) {
    super(scope, id, {
      env: props.env,
      softwareType: SoftwareType.INFRASTRUCTURE,
    });

    const namePrefix = `${SERVICE_NAME}${props.stage == 'onebox' ? '-OneBox-' : '-'}${props.stage}`;
    const dashboardName = `${namePrefix}-Dashboard`;

    const alarmFactoryDefaults: AmazonAlarmFactoryDefaults = {
      dedupeStringProcessor: new AccountSpecificDedupe(this),
      actionsEnabled: false,
      alarmNamePrefix: namePrefix,
      runbookLink: RUNBOOK_PATH_PREFIX,
    };

    const metricFactoryDefaults: AmazonMetricFactoryDefaults = {
      namespace: namePrefix,
      period: Duration.minutes(1),
    };

    const monitoringFacade = new AmazonMonitoringFacade(this, dashboardName, {
      metricDefaults: metricFactoryDefaults,
      alarmDefaults: alarmFactoryDefaults,
      dashboardNamePrefix: dashboardName,
      createDashboard: true,
      createSummaryDashboard: false,
      createAlarmDashboard: true,
      detailDashboardRange: Duration.days(7),
      summaryDashboardRange: Duration.days(7),
      createCloudWatchDashboardsRole: true,
    });

    monitoringFacade.addLargeHeader(dashboardName);
    const dashboard = monitoringFacade.createdDashboard();

    if (props.metrics.length === 0) {
      dashboard?.addWidgets(
        new TextWidget({
          markdown: `## Metrics - Not Found`,
          width: 24,
          height: 1,
        }),
      );
    } else {
      dashboard?.addWidgets(
        new TextWidget({
          markdown: `## Metrics`,
          width: 24,
          height: 1,
        }),
      );

      // Add metric widgets
      const metricWidgets = props.metrics.map(
        (metric) =>
          new GraphWidget({
            title: metric.metricName,
            left: [metric],
            width: 12,
          }),
      );
      dashboard?.addWidgets(...metricWidgets);
    }

    if (props.alarms.length === 0) {
      dashboard?.addWidgets(
        new TextWidget({
          markdown: `## Alarms - Not Found`,
          width: 24,
          height: 1,
        }),
      );
    } else {
      dashboard?.addWidgets(
        new TextWidget({
          markdown: `## Alarms`,
          width: 24,
          height: 1,
        }),
      );

      // Add alarm widgets
      const alarmWidgets = props.alarms.map(
        (alarm) =>
          new AlarmWidget({
            alarm: alarm,
            title: alarm.alarmName,
            width: 12,
          }),
      );
      dashboard?.addWidgets(...alarmWidgets);
    }
  }
}
