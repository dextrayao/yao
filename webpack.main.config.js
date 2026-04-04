const path = require('path');

module.exports = {
  mode: 'development',
  target: 'electron-main',
  entry: {
    main: './src/main/main.js',
    preload: './src/main/preload.js',
  },
  output: {
    path: path.resolve(__dirname, 'dist/main'),
    filename: '[name].js',
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env'],
          },
        },
      },
    ],
  },
  externals: {
    'better-sqlite3': 'commonjs better-sqlite3',
    '@anthropic-ai/sdk': 'commonjs @anthropic-ai/sdk',
  },
  resolve: {
    extensions: ['.js', '.jsx'],
  },
  node: {
    __dirname: false,
    __filename: false,
  },
};
