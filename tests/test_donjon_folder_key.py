from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.generate_donjon_20_level_megadungeon import slugify_folder_key, folder_key_from_args, default_raw_output_dir, default_bundle_dir


def main():
    assert slugify_folder_key('The Tenebrous Halls') == 'the_tenebrous_halls'
    assert slugify_folder_key('Árvíztűrő Tükörfúrógép') == 'arvizturo_tukorfurogep'
    args = argparse.Namespace(campaign_id='tenebrous', name='The Tenebrous Halls', folder_key=None, use_name_for_folders=False, output_dir=None, bundle_dir=None, level_start=1, level_end=20)
    assert folder_key_from_args(args) == 'tenebrous'
    assert str(default_raw_output_dir(args)) == 'campaigns/web/tenebrous_levels_1_20'
    assert str(default_bundle_dir(args)) == 'campaigns/tenebrous_bundle_v3'
    args.use_name_for_folders = True
    assert folder_key_from_args(args) == 'the_tenebrous_halls'
    args.folder_key = 'custom key!'
    assert folder_key_from_args(args) == 'custom_key'
    print('OK donjon folder key')

if __name__ == '__main__':
    main()
