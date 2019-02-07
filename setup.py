from distutils.core import setup
import os.path

setup(name='losspager',
      version='0.1dev',
      description='USGS PAGER System',
      author='Mike Hearne',
      author_email='mhearne@usgs.gov',
      url='',
      packages=['losspager', 'losspager.models', 'losspager.utils',
                'losspager.vis', 'losspager.onepager',
                'losspager.schema', 'losspager.mail',
                'losspager.io'],
      package_data={'losspager': [os.path.join('data', '*'),
                                  os.path.join('data', 'schema', '*'),
                                  os.path.join('logos', '*')
                                  ]},
      scripts=['bin/pagerlite', 'bin/emailpager',
               'bin/pager', 'bin/adminpager',
               'bin/callpager', 'bin/updatepager',
               'bin/mailadmin', 'bin/sync_users',
               'bin/twopager'])
