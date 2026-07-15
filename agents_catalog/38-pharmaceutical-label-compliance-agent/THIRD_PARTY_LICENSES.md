# Third-Party License Inventory

PharmaLabel — Pharmaceutical Label Compliance Agent

Generated: 2026-06-17  
Tooling: `pip-licenses` (Python runtime dependency closure)  
Scope: dependencies **distributed with / deployed by** the solution. Build- and test-only 
dependencies (`aws-cdk-lib`, `constructs`, `pytest`, `moto`, etc.) are excluded because they 
are not shipped to or deployed in the customer account.

## How to regenerate

```bash
python3 -m venv /tmp/lic && /tmp/lic/bin/pip install \
  -r agent_runtime_requirements.txt \
  -r custom_resources/aoss_index_creator/requirements.txt \
  -r custom_resources/runtime_resource_policy/requirements.txt pip-licenses
/tmp/lic/bin/pip-licenses --format=markdown --with-urls --order=name \
  --ignore-packages pip-licenses prettytable wcwidth tomli
```

## Summary

- Python runtime packages (incl. transitive): **81**
- Frontend vendored JavaScript: **none**
- Bundled fonts: **none**

License distribution (Python deps):

| License | Count |
|---------|-------|
| MIT | 16 |
| MIT License | 15 |
| Apache Software License | 11 |
| Apache-2.0 | 11 |
| BSD-3-Clause | 9 |
| BSD License | 7 |
| BSD-2-Clause | 2 |
| 3-Clause BSD License | 1 |
| Apache License 2.0 | 1 |
| Apache Software License; BSD License | 1 |
| Apache-2.0 AND MIT | 1 |
| Apache-2.0 OR BSD-2-Clause | 1 |
| Apache-2.0 OR BSD-3-Clause | 1 |
| MIT-CMU | 1 |
| Mozilla Public License 2.0 (MPL 2.0) | 1 |
| PSF-2.0 | 1 |
| Python Software Foundation License | 1 |

## License compatibility review

The following package(s) carry a license that is **not** on the DSR pre-approved 
license list and require reviewer sign-off:

| Package | Version | License | Notes |
|---------|---------|---------|-------|
| certifi | 2026.6.17 | Mozilla Public License 2.0 (MPL 2.0) | MPL-2.0 is weak/file-level copyleft. certifi is used unmodified as a transitive dependency (CA bundle via requests/botocore); no source modification is made or distributed. |

All remaining Python dependencies fall within the pre-approved license families
for distribution. No third-party JavaScript libraries or fonts are vendored in
the deliverable.

## Python runtime dependencies

| Package | Version | License | Source |
|---------|---------|---------|--------|
| Events | 0.5 | BSD License | http://github.com/pyeve/events |
| PyJWT | 2.13.0 | MIT | https://github.com/jpadilla/pyjwt |
| PyYAML | 6.0.3 | MIT License | https://pyyaml.org/ |
| Pygments | 2.20.0 | BSD-2-Clause | https://pygments.org |
| aiohappyeyeballs | 2.6.2 | Python Software Foundation License | https://github.com/aio-libs/aiohappyeyeballs |
| aiohttp | 3.14.1 | Apache-2.0 AND MIT | https://github.com/aio-libs/aiohttp |
| aiosignal | 1.4.0 | Apache Software License | https://github.com/aio-libs/aiosignal |
| annotated-types | 0.7.0 | MIT License | https://github.com/annotated-types/annotated-types |
| anyio | 4.14.0 | MIT | https://anyio.readthedocs.io/en/stable/versionhistory.html |
| attrs | 26.1.0 | MIT | https://www.attrs.org/en/stable/changelog.html |
| aws-requests-auth | 0.4.3 | BSD License | https://github.com/davidmuller/aws-requests-auth |
| beautifulsoup4 | 4.15.0 | MIT License | https://www.crummy.com/software/BeautifulSoup/bs4/ |
| bedrock-agentcore | 1.14.1 | Apache Software License | https://github.com/aws/bedrock-agentcore-sdk-python |
| boto3 | 1.43.31 | Apache-2.0 | https://github.com/boto/boto3 |
| botocore | 1.43.31 | Apache-2.0 | https://github.com/boto/botocore |
| certifi | 2026.6.17 | Mozilla Public License 2.0 (MPL 2.0) | https://github.com/certifi/python-certifi |
| cffi | 2.0.0 | MIT | https://cffi.readthedocs.io/en/latest/whatsnew.html |
| charset-normalizer | 3.4.7 | MIT | https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md |
| click | 8.4.1 | BSD-3-Clause | https://github.com/pallets/click/ |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography |
| dill | 0.4.1 | BSD License | https://github.com/uqfoundation/dill |
| docstring_parser | 0.18.0 | MIT License | https://github.com/rr-/docstring_parser |
| frozenlist | 1.8.0 | Apache-2.0 | https://github.com/aio-libs/frozenlist |
| grpcio | 1.81.1 | Apache-2.0 | https://grpc.io |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| httpcore | 1.0.9 | BSD-3-Clause | https://www.encode.io/httpcore/ |
| httpx | 0.28.1 | BSD License | https://github.com/encode/httpx |
| httpx-sse | 0.4.3 | MIT | https://github.com/florimondmanca/httpx-sse |
| idna | 3.18 | BSD-3-Clause | https://github.com/kjd/idna |
| jmespath | 1.1.0 | MIT License | https://github.com/jmespath/jmespath.py |
| jsonschema | 4.26.0 | MIT | https://github.com/python-jsonschema/jsonschema |
| jsonschema-specifications | 2025.9.1 | MIT | https://github.com/python-jsonschema/jsonschema-specifications |
| markdown-it-py | 4.2.0 | MIT License | https://github.com/executablebooks/markdown-it-py |
| markdownify | 1.2.2 | MIT License | http://github.com/matthewwithanm/python-markdownify |
| mcp | 1.28.0 | MIT License | https://modelcontextprotocol.io |
| mdurl | 0.1.2 | MIT License | https://github.com/executablebooks/mdurl |
| mpmath | 1.3.0 | BSD License | http://mpmath.org/ |
| multidict | 6.7.1 | Apache License 2.0 | https://github.com/aio-libs/multidict |
| opensearch-protobufs | 1.2.0 | Apache Software License | https://opensearch.org/ |
| opensearch-py | 3.2.0 | Apache Software License | https://github.com/opensearch-project/opensearch-py |
| opentelemetry-api | 1.42.1 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api |
| opentelemetry-instrumentation | 0.63b1 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/opentelemetry-instrumentation |
| opentelemetry-instrumentation-threading | 0.63b1 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python-contrib/instrumentation/opentelemetry-instrumentation-threading |
| opentelemetry-sdk | 1.42.1 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-sdk |
| opentelemetry-semantic-conventions | 0.63b1 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-semantic-conventions |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging |
| pillow | 12.2.0 | MIT-CMU | https://python-pillow.github.io |
| prompt_toolkit | 3.0.52 | BSD License | https://github.com/prompt-toolkit/python-prompt-toolkit |
| propcache | 0.5.2 | Apache Software License | https://github.com/aio-libs/propcache |
| protobuf | 7.35.1 | 3-Clause BSD License | https://developers.google.com/protocol-buffers/ |
| pycparser | 3.0 | BSD-3-Clause | https://github.com/eliben/pycparser |
| pydantic | 2.13.4 | MIT | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.14.1 | MIT | https://github.com/pydantic/pydantic-settings |
| pydantic_core | 2.46.4 | MIT | https://github.com/pydantic |
| python-dateutil | 2.9.0.post0 | Apache Software License; BSD License | https://github.com/dateutil/dateutil |
| python-dotenv | 1.2.2 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| python-multipart | 0.0.32 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| referencing | 0.37.0 | MIT | https://github.com/python-jsonschema/referencing |
| requests | 2.34.2 | Apache Software License | https://github.com/psf/requests |
| requests-aws4auth | 1.3.2 | MIT License | https://github.com/tedder/requests-aws4auth |
| rich | 14.3.4 | MIT License | https://github.com/Textualize/rich |
| rpds-py | 2026.5.1 | MIT | https://github.com/crate-py/rpds |
| s3transfer | 0.19.0 | Apache Software License | https://github.com/boto/s3transfer |
| six | 1.17.0 | MIT License | https://github.com/benjaminp/six |
| slack_bolt | 1.28.0 | MIT License | https://github.com/slackapi/bolt-python |
| slack_sdk | 3.42.0 | MIT License | https://github.com/slackapi/python-slack-sdk |
| soupsieve | 2.8.4 | MIT | https://github.com/facelessuser/soupsieve |
| sse-starlette | 3.4.4 | BSD-3-Clause | https://github.com/sysid/sse-starlette |
| starlette | 1.3.1 | BSD-3-Clause | https://github.com/Kludex/starlette |
| strands-agents | 1.44.0 | Apache Software License | https://github.com/strands-agents/harness-sdk |
| strands-agents-tools | 0.8.1 | Apache Software License | https://github.com/strands-agents/tools |
| sympy | 1.14.0 | BSD License | https://sympy.org |
| tenacity | 9.1.4 | Apache Software License | https://github.com/jd/tenacity |
| typing-inspection | 0.4.2 | MIT | https://github.com/pydantic/typing-inspection |
| typing_extensions | 4.15.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| urllib3 | 2.7.0 | MIT | https://github.com/urllib3/urllib3/blob/main/CHANGES.rst |
| uvicorn | 0.49.0 | BSD-3-Clause | https://uvicorn.dev/ |
| watchdog | 6.0.0 | Apache Software License | https://github.com/gorakhargosh/watchdog |
| websockets | 16.0 | BSD-3-Clause | https://github.com/python-websockets/websockets |
| wrapt | 2.2.1 | BSD-2-Clause | https://github.com/GrahamDumpleton/wrapt |
| yarl | 1.24.2 | Apache-2.0 | https://github.com/aio-libs/yarl |

## Frontend / bundled assets

No third-party JavaScript libraries or fonts are vendored in the repository. The
frontend uses the browser's system font stack, and all Python dependencies are
installed at deploy time from public package indexes.

## Project license

This project is distributed under **MIT-0** (see `LICENSE`).
