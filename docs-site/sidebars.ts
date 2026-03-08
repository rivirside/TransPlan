import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    { type: 'doc', id: 'intro', label: 'Introduction' },
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/quick-start',
        'getting-started/local-setup',
      ],
    },
    {
      type: 'category',
      label: 'Theory',
      items: [
        'theory/scoring-methodology',
        'theory/monte-carlo',
        'theory/competing-risks',
        'theory/wait-time-distributions',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/data-pipeline',
        'architecture/backend-api',
        'architecture/frontend',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api-reference/simulate',
        'api-reference/health',
        'api-reference/schemas',
      ],
    },
    {
      type: 'category',
      label: 'Contributing',
      items: [
        'contributing/development-guide',
        'contributing/data-curation',
        'contributing/testing',
      ],
    },
    {
      type: 'category',
      label: 'About',
      items: [
        'about/faq',
        'about/limitations',
        'about/roadmap',
      ],
    },
  ],
};

export default sidebars;
