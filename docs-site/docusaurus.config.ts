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

  url: 'https://trans-plan.vercel.app',
  baseUrl: '/docs-site/build/',

  organizationName: 'transplantmatch',
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
          // editUrl will be set when open-sourced
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
          type: 'html',
          position: 'left',
          value: '<a href="/" class="navbar__link">Home</a>',
        },
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          type: 'html',
          position: 'left',
          value: '<a href="/simulator.html" class="navbar__link">← Open App</a>',
        },
        {
          href: 'mailto:tomer@arizona.edu',
          label: 'Contact',
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
            { label: 'Contact', href: 'mailto:tomer@arizona.edu' },
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
