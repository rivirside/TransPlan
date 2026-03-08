import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'TransPlan',
  tagline: 'Probabilistic transplant location analysis',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://your-github-user.github.io',
  baseUrl: '/TransPlan/docs/',

  organizationName: 'your-github-user',
  projectName: 'TransPlan',
  trailingSlash: false,

  onBrokenLinks: 'warn',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

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
          editUrl: 'https://github.com/your-github-user/TransPlan/edit/main/docs-site/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'TransPlan',
      logo: {
        alt: 'TransPlan',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'http://localhost:8003',
          label: '← Open App',
          position: 'left',
        },
        {
          href: 'https://github.com/your-github-user/TransPlan',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Getting Started',
          items: [
            { label: 'Introduction', to: '/intro' },
            { label: 'Quick Start', to: '/getting-started/quick-start' },
            { label: 'Local Setup', to: '/getting-started/local-setup' },
          ],
        },
        {
          title: 'Theory',
          items: [
            { label: 'Scoring Methodology', to: '/theory/scoring-methodology' },
            { label: 'Monte Carlo Simulation', to: '/theory/monte-carlo' },
            { label: 'Competing Risks', to: '/theory/competing-risks' },
          ],
        },
        {
          title: 'More',
          items: [
            { label: 'API Reference', to: '/api-reference/simulate' },
            { label: 'FAQ', to: '/about/faq' },
            { label: 'GitHub', href: 'https://github.com/your-github-user/TransPlan' },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} TransPlan. For educational purposes only.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.vsDark,
      additionalLanguages: ['python', 'bash', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
