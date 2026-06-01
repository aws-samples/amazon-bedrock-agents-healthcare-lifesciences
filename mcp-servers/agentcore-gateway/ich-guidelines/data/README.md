# ICH Guideline PDFs

This directory contains ICH guideline documents used as the data source for the Bedrock Knowledge Base.

## Documents

| File | Guideline | Source |
|------|-----------|--------|
| `E6(R2) Good Clinical Practice...pdf` | ICH E6(R2) | [FDA.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e6r2-good-clinical-practice-integrated-addendum-ich-e6r1) |
| `E8(R1) GENERAL CONSIDERATIONS...pdf` | ICH E8(R1) | [FDA.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e8r1-general-considerations-clinical-studies) |
| `E9-Statistical-Principles...pdf` | ICH E9 | [FDA.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e9-statistical-principles-clinical-trials) |

## Licensing

These documents are published by the U.S. Food and Drug Administration and are in the **public domain** (U.S. Government work). They may be freely reproduced and distributed.

The ICH guidelines themselves are developed by the International Council for Harmonisation of Technical Requirements for Pharmaceuticals for Human Use (ICH) and adopted by FDA as guidance documents.

## Updating

To add new ICH guidelines:
1. Download the PDF from FDA.gov
2. Place it in this directory
3. Re-run `deploy.sh` to sync to S3 and re-index the Knowledge Base
