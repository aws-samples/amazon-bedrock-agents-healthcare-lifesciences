# Contributing Guidelines

Thank you for your interest in contributing to our project. Whether it's a bug report, new feature, correction, or additional
documentation, we greatly value feedback and contributions from our community.

Please read through this document before submitting any issues or pull requests to ensure we have all the necessary
information to effectively respond to your bug report or contribution.

## Reporting Bugs/Feature Requests

We welcome you to use the GitHub issue tracker to report bugs or suggest features.

When filing an issue, please check existing open, or recently closed, issues to make sure somebody else hasn't already
reported the issue. Please try to include as much information as you can. Details like these are incredibly useful:

* A reproducible test case or series of steps
* The version of our code being used
* Any modifications you've made relevant to the bug
* Anything unusual about your environment or deployment

## Contributing via Pull Requests

Contributions via pull requests are much appreciated. Before sending us a pull request, please ensure that:

1. You are working against the latest source on the *main* branch.
2. You check existing open, and recently merged, pull requests to make sure someone else hasn't addressed the problem already.
3. You open an issue to discuss any significant work - we would hate for your time to be wasted.

To send us a pull request, please:

1. Fork the repository.
2. Modify the source; please focus on the specific change you are contributing. If you also reformat all the code, it will be hard for us to focus on your change.
3. Ensure local tests pass.
4. Commit to your fork using clear commit messages.
5. Send us a pull request, answering any default questions in the pull request interface.
6. Pay attention to any automated CI failures reported in the pull request, and stay involved in the conversation.

GitHub provides additional document on [forking a repository](https://help.github.com/articles/fork-a-repo/) and
[creating a pull request](https://help.github.com/articles/creating-a-pull-request/).

## Finding contributions to work on

Looking at the existing issues is a great way to find something to contribute on. As our projects, by default, use the default GitHub issue labels (enhancement/bug/duplicate/help wanted/invalid/question/wontfix), looking at any 'help wanted' issues is a great place to start.

## AI-assisted development

We encourage you to use coding agents like Amazon Q Developer or Claude Code to add new agents to this repository. You can find additional information to guide this process in the `CONTEXT.md` file. In addition, we recommend the following Model Context Protocol (MCP) servers to guide coding agents:

* [AWS Documentation Server](https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server)
* [AWS CloudFormation Server](https://github.com/awslabs/mcp/tree/main/src/cfn-mcp-server)
* [Git Repo Research MCP Server](https://github.com/awslabs/mcp/tree/main/src/git-repo-research-mcp-server)

### Installation

Configure the MCP servesr in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit .amazonq/mcp.json):

```json
{
    "mcpServers": {
        "awslabs.aws-documentation-mcp-server": {
            "command": "uvx",
            "args": [
                "awslabs.aws-documentation-mcp-server@latest"
            ],
            "env": {
                "FASTMCP_LOG_LEVEL": "ERROR",
                "AWS_DOCUMENTATION_PARTITION": "aws"
            },
            "disabled": false,
            "autoApprove": []
        },
        "awslabs.cfn-mcp-server": {
            "command": "uvx",
            "args": [
                "awslabs.cfn-mcp-server@latest"
            ],
            "env": {
                "AWS_PROFILE": "YOUR_AWS_PROFILE_NAME"
            },
            "disabled": false,
            "autoApprove": []
        },
        "awslabs.git-repo-research-mcp-server": {
            "command": "uvx",
            "args": [
                "awslabs.git-repo-research-mcp-server@latest"
            ],
            "env": {
                "AWS_PROFILE": "YOUR_AWS_PROFILE_NAME",
                "AWS_REGION": "YOUR_AWS_REGION",
                "FASTMCP_LOG_LEVEL": "ERROR",
                "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN"
            },
            "disabled": false,
            "autoApprove": []
        }
    }
}
```

Replace `YOUR_AWS_PROFILE_NAME`, `YOUR_AWS_REGION`, and `YOUR_GITHUB_TOKEN` with the correct values.

### Prompt

For best results, ensure that your prompt is clear and consise. As an example, here is the prompt used to create the UniProt-protein-research agent:

> I would like to create a new agent in this repository for retrieving information about proteins from UniProt. Scientists need information about specific proteins to answer questions like, "Which protein might be the cause of a disease"? This information could include human-readable descriptions of protein function, metadata about where a protein is commonly located in a cell, or amino acid sequence information. UniProt provides several APIs to retrieve information about proteins programmatically. An overview of these APIs can be found at https://www.uniprot.org/api-documentation/uniprotkb. You can also find detailed Swagger documentation for these APIs at https://www.uniprot.org/api-documentation/uniprotkb.  Please help me create a new Bedrock Agent that can take in the name or description of a protein, search for it using an ActionGroup linked to the UniProt search API, then retrieve details for one or more specific proteins of interest by their UniProtKB accession ID.

## Code of Conduct

This project has adopted the [Amazon Open Source Code of Conduct](https://aws.github.io/code-of-conduct).
For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq) or contact
<opensource-codeofconduct@amazon.com> with any additional questions or comments.

## Security issue notifications

If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.

## Licensing

See the [LICENSE](LICENSE) file for our project's licensing. We will ask you to confirm the licensing of your contribution.
