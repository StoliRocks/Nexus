/**
 * Generates a fully qualified name for an alarm.
 * @param name Name of the alarm
 * @param severity Alarm severity ex. Sev2, Sev3, etc.
 * @param stage Stage
 * @param awsRegion AWS Region.
 */
export function generateQualifiedAlarmName(name: string, severity: string, stage: string, awsRegion: string): string {
  return `${severity}-${name}-${stage}-${awsRegion}`.replace(/[^a-zA-Z0-9-]/g, '-');
}
