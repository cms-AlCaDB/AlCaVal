'''
Module containing the functions necessary to interact with the wma.
Credit and less than optimal code has to be spreaded among lots of people.
'''
import os
#pylint: disable=deprecated-module
import imp
#pylint: enable=deprecated-module
import argparse
#pylint: disable=import-error
from tweak_maker_lite import TweakMakerLite
from config_cache_lite import ConfigCacheLite
#pylint: enable=import-error


def load_config_file(file_path):
    """
    Load a config module
    """
    print('Importing the config, this may take a while...')
    config_base_name = os.path.basename(file_path).replace(".py", "")
    config_dir_name = os.path.dirname(file_path)
    module_path = imp.find_module(config_base_name, [config_dir_name])
    loaded_config = imp.load_module(config_base_name,
                                    module_path[0],
                                    module_path[1],
                                    module_path[2])
    print('Imported %s' % (file_path))
    return loaded_config


def upload_to_couch(cfg_file_name, label, user_name, group_name, database_url):
    """
    Upload config file to ReqMgr config database - "config cache"
    """
    if not os.path.exists(cfg_file_name):
        raise Exception('Can\'t locate config file %s.' % cfg_file_name)

    loaded_config = load_config_file(cfg_file_name)
    config_cache = ConfigCacheLite(database_url)
    config_cache.set_user_group(user_name, group_name)
    config_cache.add_config(cfg_file_name)
    tweaks = TweakMakerLite().make(loaded_config.process)
    config_cache.set_PSet_tweaks(tweaks)
    config_cache.set_label(label)
    config_cache.set_description(label)
    config_cache.save()

    print('DocID    %s %s' % (label, config_cache.document['_id']))
    print('Revision %s %s' % (label, config_cache.document['_rev']))

    return config_cache.document['_id']


def main():
    """
    Main function - parse arguments and upload config to couch
    """
    parser = argparse.ArgumentParser(description='Upload config file to config database')
    parser.add_argument('--file',
                        dest='filename',
                        type=str,
                        help='File to be uploaded')
    parser.add_argument('--label',
                        type=str,
                        help='Label, e.g. prepid')
    parser.add_argument('--user',
                        type=str,
                        help='Username')
    parser.add_argument('--group',
                        type=str,
                        help='Group')
    parser.add_argument('--db',
                        type=str,
                        help='Database url')


    args = parser.parse_args()
    upload_to_couch(args.filename, args.label, args.user, args.group, args.db)


if __name__ == '__main__':
    main()