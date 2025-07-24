# Clinical evidence researcher Agent

This agent is a collaborator agent used by a supervisor agent for Cancer biomarker discovery. You can find details of its deployment and usage in multi-agent collaboration mode in [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

This agent retrieves and summarize insights from scientific literature. PubMed APIs to search biomedical literature for external evidence. Use Amazon Bedrock Knowledge Bases for Retrieval Augmented Generation (RAG) to deliver responses from internal literature evidence.

## Features

- **PubMed abstract search**: Searches with the PubMed API for relevant abstracts and provides details including title and citations
- **Full text document search**: Searches from a sample full text document indexed in a Bedrock Knowledge Base using RAG techniques

Here are some example questions that can be answered by this agent.

    * Can you search PubMed for FDA approved biomarkers for non small cell lung cancer?
    * What properties of the tumor are associated with metagene 19 activity and EGFR pathway?
    * According to the knowledge base evidence study, how many semantic image features were initially recorded for each tumor?


### Deployment

 Deploy the entire stack of collaborator agents for [Cancer Biomarker Discovery Example](../../multi_agent_collaboration/cancer_biomarker_discovery/README.md).

Step by step instructions of deploying and testing the agent are included in the notebook. 

## How to Test in AWS Console

1. Go to [Amazon Bedrock](https://console.aws.amazon.com/bedrock) and select **Agents.**

2. Select your  agent and test by asking questions in **Test** window on your right. 

## License

- [MIT-0](/LICENSE)