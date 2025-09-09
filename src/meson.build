pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'pyrose'
gnome = import('gnome')
blueprints = custom_target('blueprints',
  input: files(
    'window.blp',
    'code_view.blp',
    'preferences.blp',
    'symbol_chooser.blp',
    'terminal.blp',
    'gtk/help-overlay.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTPUT@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

gnome.compile_resources('pyrose',
  'pyrose.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
  dependencies: blueprints,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'pyrose.in',
  output: 'pyrose',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

pyrose_sources = [
  '__init__.py',
  'code_view.py',
  'completion_provider.py',
  'helpers.py',
  'hover_provider.py',
  'main.py',
  'window.py',
  'lsp_client.py',
  'pango_utils.py',
  'preferences.py',
  'symbol_chooser.py',
  'terminal.py'
]

install_data(pyrose_sources, install_dir: moduledir)