import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'ForkFlux',
  tagline: 'Coordination bus for AI agents',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://docs.forkflux.ai',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'forkflux', // Usually your GitHub org/user name.
  projectName: 'forkflux', // Usually your repo name.

  onBrokenLinks: 'throw',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/og-image.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'ForkFlux',
      logo: {
        alt: 'Coordination bus for AI agents',
        src: 'img/logo.png',
      },
      items: [
        {
          href: 'https://github.com/forkflux/forkflux',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {
              label: 'Docs',
              to: '/',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'LinkedIn',
              href: 'https://linkedin.com/company/forkflux/',
            },
            {
              label: 'Discord',
              href: 'https://discord.com/invite/wTJVctJwn3',
            },
            {
              label: 'X',
              href: 'https://x.com/forkflux',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/forkflux/forkflux',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} ForkFlux. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
    algolia: {
      appId: 'B59BOY5381',
      apiKey: '0f89879687452cc869902f79cd4fbb51',
      indexName: 'docs',
      contextualSearch: false,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
