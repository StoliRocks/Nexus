import { Runtime } from 'aws-cdk-lib/aws-lambda';
import { readFileSync } from 'node:fs';
import * as brazil from '@amzn/brazil';

/**
 * Reads the version of `Python-default` configured for the current versionset
 */
function brazilPythonDefaultRuntime(): Runtime {
  const libPath = brazil.runPathRecipeSync('[Python-default-for-BATS-lambda]pkg.lib');
  const pyVer = readFileSync(`${libPath}/Python-default-runtime`).toString().trim();
  const pythonDefaultRuntime = Runtime.ALL.find((r) => r.name === `python${pyVer}`);
  if (pythonDefaultRuntime === undefined) {
    throw new Error('Unable to determine the Python-default version');
  }
  return pythonDefaultRuntime;
}

export const DEFAULT_BRAZIL_PYTHON_RUNTIME = brazilPythonDefaultRuntime();
