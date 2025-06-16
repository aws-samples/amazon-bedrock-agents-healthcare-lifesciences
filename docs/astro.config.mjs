import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://aws-samples.github.io',
  base: '/amazon-bedrock-agents-healthcare-lifesciences/',
  trailingSlash: 'always',
  integrations: [starlight({
    title: 'Sample Agents for Healthcare and Life Sciences on AWS',
    social: {
      github: 'https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main',
    },
    sidebar: [
      {
        label: 'Getting Started',
        items: [
          { label: 'Introduction', link: '/' },
          { label: 'GitHub', link: 'https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main' },
        ]
      },
      {
        label: 'Components',
        items: [
          { label: 'Agents Catalog', link: 'https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main/agents_catalog' },
          { label: 'Multi-Agent Orchestration', link: 'https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main/multi_agent_collaboration/' },
          { label: 'Deployment', link: 'https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main?tab=readme-ov-file#deployment' },
          { label: 'Evaluations', link: 'https://github.com/aws-samples/amazon-bedrock-agents-healthcare-lifesciences/tree/main/evaluations' },
        ]
      },
    ],
  }), mdx()],
});
