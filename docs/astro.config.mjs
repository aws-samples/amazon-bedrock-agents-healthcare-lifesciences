import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://aws-samples.github.io',
  base: '/amazon-bedrock-agents-healthcare-lifesciences/',
  trailingSlash: 'always',
  integrations: [starlight({
    title: 'Amazon Bedrock Agents for Healthcare and LifeSciences',
    social: {
      github: 'https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery/tree/multi-agent-collaboration',
    },
    sidebar: [
      {
        label: 'Getting Started',
        items: [
          { label: 'Introduction', link: '/' },
          { label: 'Setup', link: '/setup/' },
        ]
      },
      {
        label: 'Components',
        items: [
          { label: 'Agents Catalog', link: './agents_catalog/' },
          { label: 'Multi-Agent Orchestration', link: './multi_agent_orchestration/' },
          { label: 'Deployment', link: './deployment/' },
          { label: 'Evaluations', link: './evaluations/' },
        ]
      },
    ],
  }), mdx()],
});
