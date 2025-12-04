## Welcome!

This package will help you manage Pipelines and your AWS infrastructure with the power of CDK!

You can view this pipeline [NexusApplicationPipeline](https://pipelines.amazon.com/pipelines/NexusApplicationPipeline)

# Development

```bash
brazil ws create --name NexusApplicationInfrastructure
cd NexusApplicationInfrastructure
brazil ws use \
  --versionset NexusApplicationPipeline/development \
  --platform AL2_x86_64 \
  --package NexusApplicationInfrastructureCDK
cd src/NexusApplicationInfrastructureCDK
brazil-build
```

**Note:** If dependent packages are checked out, building them is required to successfully execute `NexusApplicationInfrastructureCDK`.

## Add New Accounts/Stages/Regions to pipeline

```
brazil-build deploy:bootstrap
```

Run above command from `NexusApplicationInfrastructureCDK` when new Account/Region/Stage needs to be added to pipeline.

## Making code changes for Pipeline

- Make required code changes to pipeline
- `bb` in `NexusApplicationInfrastructureCDK`
- Verify your changes by executing `bb diff:pipeline`
- Verify changes in diff looks correct, send code review and merge it. As code propagates though pipeline, it will make changes as per new commit.

# Builds

- Build your CDK application

```bash
brazil-build
```

- List stack Ids

```bash
brazil-build cdk list
```

The output should contain the following stacks:

```bash
BONESBootstrap-disambiguator-awsAccountID-AWSRegion
```

- Deploy your personal BONESBootstrap stack. Be sure to specify the name of your personal bootstrap stack.
  This will bootstrap only the new environment, rather than rebootstrapping all environments that your pipeline deploys to, including production environments.

```bash
brazil-build bootstrap BONESBootstrap-7425380-042218206589-us-east-1
```

- Deploy your application stack for the first time:

```bash
brazil-build cdk deploy APIEndpointHandler-042218206589-us-east-1-beta
```

# Verify

1. Check what is in `NexusAPIEndpointHandlerLambda-1.0` environment

   - Add `NexusAPIEndpointHandlerLambda` as a package `brazil ws add -P NexusAPIEndpointHandlerLambda`.
   - cd `src/NexusAPIEndpointHandlerLambda`
   - Run `brazil-runtime-exec NexusAPIEndpointHandlerLambda-1.0`
   - Explore `ls al ../../env/NexusAPIEndpointHandlerLambda-1.0`

2. Run docker image locally

- `cd src/NexusAPIEndpointHandlerLambda && bb clean && bb release`
- `cd src/NexusApplicationInfrastructureCDK && bb`

```bash
export GENERATED_IMAGE=$(
bats --debug transform \
--type DockerImage-1.0 \
--target NexusAPIEndpointHandlerLambda-1.0 \
--parameter NexusAPIEndpointHandlerLambda-1.0
)
```

- Run docker container:

```bash
docker run -p 9000:8080 $GENERATED_IMAGE
```

- Access bash/shell

```bash
docker exec -it $(docker ps -q) sh
```

- View logs emitted by Docker container

```bash
docker logs $(docker ps -q)
```

# Troubleshooting

## Deployment fails

`APIEndpointHandler-677276089853-us-west-2-beta failed: ValidationError: Stack [APIEndpointHandler-677276089853-us-west-2-beta] cannot be deleted while TerminationProtection is enabled
 ›   Error: Failed to run CDK CLI`

_Assuming this as a non-prod stage, you need to redeploy your application after deleting the Pipeline-_ stack from AWS CloudFormation Console in the region.
Once delete is successful and the stack is recreated after deployment, all the subsequent deployments will only cause an update operation to your stack,
and hence won't require you to manually pass a .terminationProtection flag.\*

## Force delete stacks

```bash
aws cloudformation delete-stack --stack-name STACK_NAME --deletion-mode FORCE_DELETE_STACK
```

## Pipeline

### Pipeline failures

#### Packaging failures

##### Failure

`EXCEPTION: com.amazon.coral.service.accessdeniedexception.AccessDeniedException: <AccessDeniedException(message='User arn:aws:iam::430427536594:user/bats-auth-user is not authorized to perform sts:AssumeRole.')> [bats_workflow.public.authentication] Traceback (most recent call last): File "/apollo/env/BATSWorkflow2/lib/python3.10/site-packages/bats_workflow/authentication.py", line 218, in _ars_assume_role ars_response = self.ars.assume_role( File "/apollo/env/BATSWorkflow2/lib/python3.10/site-packages/coral/service/__init__.py", line 145, in closure return self._coral_call(in_value, method_spec) File "/apollo/env/BATSWorkflow2/lib/python3.10/site-packages/coral/service/__init__.py", line 366, in _coral_call return self._parse_call_reply(method_spec, reply) File "/apollo/env/BATSWorkflow2/lib/python3.10/site-packages/coral/service/__init__.py", line 401, in _parse_call_reply raise found_exception.__from_coral__(**coral_reply) com.amazon.coral.service.accessdeniedexception.AccessDeniedException: <AccessDeniedException(message='User arn:aws:iam::430427536594:user/bats-auth-user is not authorized to perform sts:AssumeRole.')>`

**Fix**

`430427536594` is an internal to Amazon account with permissions to deploy to AWS accounts. A missing permission can indicate that the pipeline is not yet onboarded to this account. Deploy pipeline with `--onboard` flag.

1. Bootstrap each account

```bash
brazil-build bootstrap
```

2. Deploy pipeline

```bash
pipeline deploy --onboard
```

### Delete pipeline

```bash
brazil-build cdk destroy Pipeline-NexusApplicationInfrastructure
```

### Bootstrap all accounts

```bash
brazil-build bootstrap
```

### Bootstrap failures

#### Failure

`BONESBootstrap-7425380-416411036610-us-east-1 failed: ToolkitError: Failed to create ChangeSet cdk-deploy-change-set on BONESBootstrap-7425380-416411036610-us-east-1: FAILED, The resources [BARS772963B4] already exist in your account, but they cannot be imported in this operation because they depend on resources [BARSBARSKey008C869E] that are not eligible for automatic import. Retry the operation after importing the existing resources with an IMPORT-type change set or removing the existing resources from your account.`

**Fix**
One or all accounts may have residual artifacts in S3. Delete all `deployment*` buckets from S3. If the error doesn't go away, check for any residual repository in `AmazonECR -> Private Registry -> bars*` and delete registries.

### Deploy pipeline

Reference: https://docs.hub.amazon.dev/pipelines/cli-guide/howto-deploy/

```bash
pipeline deploy --onboard
```

## Docker useful commands

- List running docker instance `docker ps`
- Get access to shell of the running docker instance `docker exec -it $(docker ps -q) sh`
- List all local docker images `docker images -a`. To get only image ids, run `docker images -a -q`
- Cleanup docker containers by forcefully removing all images `docker rmi $(docker images -q) -f`

## Inspect Lambda Contents

### Create lambda zip

```bash
bats transform --target NexusAPIEndpointHandlerLambda-1.0 --type NexusAPIEndpointHandlerLambda-1.0 --parameter NexusAPIEndpointHandlerLambda-1.0
```

### Check size

```bash
ls -lh aws_lambda.bundle.primary.*.zip
```

### Extract and inspect

```bash
mkdir /tmp/lambda_contents
unzip aws_lambda.bundle.primary.*.zip -d /tmp/lambda_contents
du -sh /tmp/lambda_contents # Total size of unzipped files
du -h --max-depth=1 /tmp/lambda_contents  # Size of each folder
```

## Useful links:

- [Adding stages to your pipeline](https://docs.hub.amazon.dev/pipelines/cdk-guide/howto-cdk-expand-pipeline/)
- [How to full wash cycle CDK pipeline stacks](https://docs.hub.amazon.dev/pipelines/cdk-guide/howto-cdk-rebootstrap-pipeline/)
- [NAWS Deployment and Bootstrap Stack Issue Runbook](https://w.amazon.com/bin/view/ContinuousDeployment/Internal/AwsIntegrationsTeam/Runbooks/BootstrapStackRunbook/)
- [NativeAWS's how-to guides](https://builderhub.corp.amazon.com/docs/native-aws/developer-guide/)
- [Pipelines constructs references](https://code.amazon.com/packages/PipelinesConstructs/blobs/mainline/--/README.md)
- [CDK constructs references](https://docs.aws.amazon.com/cdk/api/latest/versions.html)
- [Catalogue of CDK libraries](https://builderhub.corp.amazon.com/docs/native-aws/developer-guide/cdk-construct-libraries.html)
