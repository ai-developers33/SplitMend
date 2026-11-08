"""Confirm that every benchmark uses the released v0.1.1 core bytes."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = ['package/src/splitmend','original/SplitMend/src/splitmend',
             'benchmarks/single_group/vendor/splitmend','benchmarks/bridge/vendor/splitmend']
    checks = []
    with zipfile.ZipFile(ROOT/'package/dist/splitmend-0.1.1-py3-none-any.whl') as wheel:
        for path in sorted((ROOT/paths[0]).glob('*.py')):
            released = wheel.read('splitmend/'+path.name)
            digest = hashlib.sha256(released).hexdigest()
            for folder in paths:
                actual = hashlib.sha256((ROOT/folder/path.name).read_bytes()).hexdigest()
                assert actual == digest, (folder,path.name)
            checks.append({'file':path.name,'wheel_sha256':digest,'all_four_source_copies_match':True})
    result = {'version':'0.1.1','checks':checks,'all_match':True}
    print(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    main()
