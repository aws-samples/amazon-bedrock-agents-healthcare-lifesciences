import { Bucket } from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";

export function setSecureTransport(bucket: Bucket): void {
  bucket.addToResourcePolicy(
    new iam.PolicyStatement({
      sid: "DenyInsecureConnections",
      effect: iam.Effect.DENY,
      principals: [new iam.AnyPrincipal()],
      actions: ["s3:*"],
      resources: [bucket.bucketArn, `${bucket.bucketArn}/*`],
      conditions: {
        Bool: {
          "aws:SecureTransport": "false",
        },
      },
    })
  );
}