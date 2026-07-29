import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Start here',
      items: ['general/intro', 'general/quickstart', 'general/manual-setup'],
    },
    {
      type: 'category',
      label: 'Learn ForkFlux',
      items: ['general/core-concepts', 'general/faq'],
    },
    {
      type: 'category',
      label: 'Integrate',
      items: [
        'general/mcp-integration',
        'general/workflow-helpers',
        'general/plugins',
        'general/cli',
      ],
    },
    {type: 'category', label: 'Operate', items: ['general/self-hosting']},
    {type: 'category', label: 'Contribute', items: ['general/contributing']},
  ],
  openApiSidebar: [
    {
      type: 'category',
      label: 'API Reference',
      link: {
        type: 'generated-index',
        title: 'ForkFlux API',
        slug: '/api-reference',
      },
      items: require('./docs/api-reference/sidebar.ts'),
    },
  ],
};

export default sidebars;
