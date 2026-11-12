# ns8-ui-lib

This library includes [Vue.js](https://vuejs.org/) UI components and mixins used by [NethServer 8](https://github.com/NethServer/ns8-core) UI.

Browse the components in the [Storybook](https://nethserver.github.io/ns8-ui-lib/), published for each release.

Documentation of NS8 UI library can be found in [this section of the Developer manual](https://nethserver.github.io/ns8-core/ui/library/).

## Development

Install dependencies, needed only the first time:

```bash
npm install
```

Build the library:

```bash
npm run build
```

Start Storybook, to explore and test the components:

```bash
NODE_OPTIONS=--openssl-legacy-provider npm run storybook
```

Start the playground, a local app to quickly test components (e.g. to reproduce a bug or to combine several components):

```bash
NODE_OPTIONS=--openssl-legacy-provider npm run playground
```

Edit `playground/App.vue` for your tests, but do not commit your changes.

`NODE_OPTIONS` is needed with recent Node.js versions, since Storybook and the playground use webpack 4.

See the [Developer manual](https://nethserver.github.io/ns8-core/ui/library/) for development containers, releases and testing a development version inside NS8 core or modules.
