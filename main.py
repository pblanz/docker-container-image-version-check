import json
import pprint
import requests
import subprocess

from packaging import version
from tabulate import tabulate

#url_docker_api = "https://registry.hub.docker.com/api/content/v1/repositories/public/library/REPO/tags?page=1&page_size=PAGE_SIZE"
url_docker_api = "https://hub.docker.com/v2/repositories/library/REPO/tags?page=1&page_size=PAGE_SIZE"
outs = subprocess.check_output(["docker", "container", "ls", "--format='{{json .}}'"]).decode('utf8')
versions = {}

def remove_digits_from_string(s):
    if s:
        return ''.join([i for i in s if not i.isdigit()])

def get_version_number(version_number):
    version_number = version_number.split('-')
    ver = version.parse(version_number[0])
    if len(version_number) == 1:
        suffix = None
    else:
        suffix = '-'.join(version_number[1:])
    return ver, suffix

for out in outs.split('\n'):
    if not out:
        continue

    out=out.replace('\\"','').replace('\'','')
    j = json.loads(out)

    id = j['ID']
    image = j['Image']
    image_url, image_version_local = image.split(":")
    name = j['Names']
    
    try:
        version_local, suffix_local = get_version_number(image_version_local)
    except version.InvalidVersion:
        continue

    versions[name] = {"version_local": version_local, "version_suffix": suffix_local, "versions_online": list()}
    url = url_docker_api.replace('REPO', image_url).replace('PAGE_SIZE', '100')

    if '/' in image_url:
        url = url.replace('library/', '')

    r = requests.get(url)

    j = json.loads(r.text)
    j_results = j['results']

    image_versions_online = [i['name'] for i in j_results]

    for version_online in image_versions_online:
        try:
            version_online, suffix_online = get_version_number(version_online)
        except version.InvalidVersion:
            continue
       
        if remove_digits_from_string(suffix_local) != remove_digits_from_string(suffix_online):
            continue

        if version_online.is_prerelease:
            continue

        versions[name]["versions_online"].append(version_online)

headers = ["Container", "Upgradable", "Local Version", "Online Version"]
rows = list()

for container_name, vers in versions.items():
    upgradable = False
    version_local = vers["version_local"]
    versions_online = vers["versions_online"]
    highest_version_online = max(versions_online)
    if (highest_version_online > version_local):
        upgradable = True
    rows.append([str(container_name), str(upgradable), str(version_local), str(highest_version_online)])

print(tabulate(rows, headers=headers))

