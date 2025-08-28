import { RemovalPolicy } from "aws-cdk-lib";

const projectName = "MedicalDeviceApp";

const s3BucketProps = {
  autoDeleteObjects: true,
  removalPolicy: RemovalPolicy.DESTROY,
};

type EnvNameType = "dev" | "prod";

export { projectName, s3BucketProps, EnvNameType };