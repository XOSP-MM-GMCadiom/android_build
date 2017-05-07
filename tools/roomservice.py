#!/usr/bin/env python
#!/usr/bin/env python2

# Copyright (C) 2012-2013, The CyanogenMod Project
# Copyright (C) 2013 Cybojenix <anthonydking@gmail.com>
# Copyright (C) 2013 The OmniROM Project
# Copyright (C) 2014/2015 crDroid Android
#           (C) 2017,      The LineageOS Project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import json
import sys
import os
import re
from xml.etree import ElementTree as ES
# Use the urllib importer from the Cyanogenmod roomservice
try:
    # For python3
    import urllib.request
except ImportError:
  # For python2
  import imp
  import urllib2
  import urlparse
  urllib = imp.new_module('urllib')
  urllib.error = urllib2
  urllib.parse = urlparse
  urllib.request = urllib2

from xml.etree import ElementTree

product = sys.argv[1]

if len(sys.argv) > 2:
    depsonly = sys.argv[2]
else:
    depsonly = None

try:
    device = product[product.index("_") + 1:]
except:
    device = product

if not depsonly:
    print("Device %s not found. Attempting to retrieve device repository from XOSP Github (http://github.com/XOSP)." % device)

repositories = []

try:
    authtuple = netrc.netrc().authenticators("api.github.com")

    if authtuple:
        auth_string = ('%s:%s' % (authtuple[0], authtuple[2])).encode()
        githubauth = base64.encodestring(auth_string).decode().replace('\n', '')
    else:
        githubauth = None
except:
    githubauth = None

def add_auth(githubreq):
    if githubauth:
        githubreq.add_header("Authorization","Basic %s" % githubauth)

if not depsonly:
    githubreq = urllib.request.Request("https://api.github.com/search/repositories?q=%s+user:XOSP+in:name+fork:true" % device)
    add_auth(githubreq)
    try:
        response = urllib.request.urlopen(git_req)
    except urllib.request.HTTPError:
        raise Exception("There was an issue connecting to github."
                        " Please try again in a minute")
    git_data = json.load(response)
    check_repo_exists(git_data)
    print("found the {} device repo".format(device))
    return git_data


def get_device_url(git_data):
    device_url = ""
    for item in git_data['items']:
        temp_url = item.get('html_url')
        if "{}/android_device".format(android_team) in temp_url:
            try:
                temp_url = temp_url[temp_url.index("android_device"):]
            except ValueError:
                pass
            else:
                if temp_url.endswith(device):
                    device_url = temp_url
                    break

    if device_url:
        return device_url
    raise Exception("{} not found in {} Github, exiting "
                    "roomservice".format(device, android_team))


def parse_device_directory(device_url,device):
    to_strip = "android_device"
    repo_name = device_url[device_url.index(to_strip) + len(to_strip):]
    repo_name = repo_name[:repo_name.index(device)]
    repo_dir = repo_name.replace("_", "/")
    repo_dir = repo_dir + device
    return "device{}".format(repo_dir)


# Thank you RaYmAn
def iterate_manifests(check_all):
    files = []
    if check_all:
        for file in os.listdir(local_manifest_dir):
            files.append(os.path.join(local_manifest_dir, file))
    files.append('.repo/manifest.xml')
    for file in files:
        try:
            man = ES.parse(file)
            man = man.getroot()
        except IOError, ES.ParseError:
            print("WARNING: error while parsing %s" % file)
        else:
            for project in man.findall("project"):
                yield project


def check_project_exists(url):
    for project in iterate_manifests(True):
        if project.get("name") == url:
            return True
    return False


def check_dup_path(directory):
    for project in iterate_manifests(False):
        if project.get("path") == directory:
            print ("Duplicate path %s found! Removing" % directory)
            return project.get("name")
    return None


# Use the indent function from http://stackoverflow.com/a/4590052
def indent(elem, level=0):
    i = ''.join(["\n", level*"  "])
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = ''.join([i, "  "])
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def create_manifest_project(url, directory,
                            remote=default_rem,
                            revision=default_rev):
    project_exists = check_project_exists(url)

    if project_exists:
        return None

    dup_path = check_dup_path(directory)
    if not dup_path is None:
            write_to_manifest(
                append_to_manifest(
                    create_manifest_remove(dup_path)))

    project = ES.Element("project",
                         attrib={
                             "path": directory,
                             "name": url,
                             "remote": remote,
                             "revision": revision
                         })
    return project


def create_manifest_remove(url):
    remove = ES.Element("remove-project", attrib={"name": url})
    return remove


def append_to_manifest(project):
    try:
        lm = ES.parse('/'.join([local_manifest_dir, "roomservice.xml"]))
        lm = lm.getroot()
    except:
        lm = ElementTree.Element("manifest")

    for repository in repositories:
        repo_name = repository['repository']
        repo_target = repository['target_path']
        print('Checking if %s is fetched from %s' % (repo_target, repo_name))
        if is_in_manifest(repo_target):
            print('XOSP/%s already fetched to %s' % (repo_name, repo_target))
            continue

        print('Adding dependency: XOSP/%s -> %s' % (repo_name, repo_target))
        project = ElementTree.Element("project", attrib = { "path": repo_target,
            "remote": "github", "name": "XOSP/%s" % repo_name })

        if 'branch' in repository:
            project.set('revision',repository['branch'])
        elif fallback_branch:
            print("Using fallback branch %s for %s" % (fallback_branch, repo_name))
            project.set('revision', fallback_branch)
        else:
            print("Using default branch for %s" % repo_name)


def write_to_manifest(manifest):
    indent(manifest)
    raw_xml = ES.tostring(manifest).decode()
    raw_xml = ''.join(['<?xml version="1.0" encoding="UTF-8"?>\n'
                       '<!--Please do not manually edit this file-->\n',
                       raw_xml])

    with open('/'.join([local_manifest_dir, "roomservice.xml"]), 'w') as f:
        f.write(raw_xml)
    print("wrote the new roomservice manifest")

def fetch_dependencies(repo_path, fallback_branch = None):
    print('Looking for dependencies')
    dependencies_paths = [repo_path + '/xosp.dependencies', repo_path + '/lineage.dependencies', repo_path + '/cm.dependencies']
    found_dependencies = False
    syncable_repos = []

    for dependencies_path in dependencies_paths:
        if os.path.exists(dependencies_path):
            dependencies_file = open(dependencies_path, 'r')
            dependencies = json.loads(dependencies_file.read())
            fetch_list = []

            for dependency in dependencies:
                if not is_in_manifest(dependency['target_path']):
                    fetch_list.append(dependency)
                    syncable_repos.append(dependency['target_path'])

            dependencies_file.close()
            found_dependencies = True

            if len(fetch_list) > 0:
                print('Adding dependencies to manifest')
                add_to_manifest(fetch_list, fallback_branch)
            break

    if not found_dependencies:
        print('Dependencies file not found, bailing out.')

    if len(syncable_repos) > 0:
        print('Syncing dependencies')
        os.system('repo sync --force-sync %s' % ' '.join(syncable_repos))


def parse_dependency_file(location):
    dep_file = "xosp.dependencies"
    dep_location = '/'.join([location, dep_file])
    if not os.path.isfile(dep_location):
        print("WARNING: %s file not found" % dep_location)
        sys.exit()
    try:
        with open(dep_location, 'r') as f:
            dependencies = json.loads(f.read())
    except ValueError:
        raise Exception("ERROR: malformed dependency file")
    return dependencies


def create_dependency_manifest(dependencies):
    projects = []
    for dependency in dependencies:
        repository = dependency.get("repository")
        target_path = dependency.get("target_path")
        revision = dependency.get("revision", default_rev)
        remote = dependency.get("remote", default_rem)

        # not adding an organization should default to android_team
        # only apply this to github
        if remote == "github":
            if not "/" in repository:
                repository = '/'.join([android_team, repository])
        project = create_manifest_project(repository,
                                          target_path,
                                          remote=remote,
                                          revision=revision)
        if not project is None:
            manifest = append_to_manifest(project)
            write_to_manifest(manifest)
            projects.append(target_path)
    if len(projects) > 0:
        os.system("repo sync -f --force-sync --no-clone-bundle %s" % " ".join(projects))


def fetch_dependencies(device):
    location = parse_device_from_folder(device)
    if location is None or not os.path.isdir(location):
        raise Exception("ERROR: could not find your device "
                        "folder location, bailing out")
    dependencies = parse_dependency_file(location)
    create_dependency_manifest(dependencies)


def check_device_exists(device):
    location = parse_device_from_folder(device)
    if location is None:
        return False
    return os.path.isdir(location)


def fetch_device(device):
    if check_device_exists(device):
        print("WARNING: Trying to fetch a device that's already there")
        return
    git_data = search_github_for_device(device)
    device_url = android_team+"/"+get_device_url(git_data)
    device_dir = parse_device_directory(device_url,device)
    project = create_manifest_project(device_url,
                                      device_dir,
                                      remote=default_team_rem)
    if not project is None:
        manifest = append_to_manifest(project)
        write_to_manifest(manifest)
        print("syncing the device config")
        os.system('repo sync -f --force-sync --no-clone-bundle %s' % device_dir)


if __name__ == '__main__':
    if not os.path.isdir(local_manifest_dir):
        os.mkdir(local_manifest_dir)

    product = sys.argv[1]
    try:
        device = product[product.index("_") + 1:]
    except ValueError:
        device = product

    if len(sys.argv) > 2:
        deps_only = sys.argv[2]
    else:
        print("Trying dependencies-only mode on a non-existing device tree?")

    sys.exit()

else:
    for repository in repositories:
        repo_name = repository['name']
        if re.match(r"^android_device_[^_]*_" + device + "$", repo_name):
            print("Found repository: %s" % repository['name'])
            
            manufacturer = repo_name.replace("android_device_", "").replace("_" + device, "")
            
            default_revision = get_default_revision()
            print("Default revision: %s" % default_revision)
            print("Checking branch info")
            githubreq = urllib.request.Request(repository['branches_url'].replace('{/branch}', ''))
            add_auth(githubreq)
            result = json.loads(urllib.request.urlopen(githubreq).read().decode())

            ## Try tags, too, since that's what releases use
            if not has_branch(result, default_revision):
                githubreq = urllib.request.Request(repository['tags_url'].replace('{/tag}', ''))
                add_auth(githubreq)
                result.extend (json.loads(urllib.request.urlopen(githubreq).read().decode()))
            
            repo_path = "device/%s/%s" % (manufacturer, device)
            adding = {'repository':repo_name,'target_path':repo_path}
            
            fallback_branch = None
            if not has_branch(result, default_revision):
                if os.getenv('ROOMSERVICE_BRANCHES'):
                    fallbacks = list(filter(bool, os.getenv('ROOMSERVICE_BRANCHES').split(' ')))
                    for fallback in fallbacks:
                        if has_branch(result, fallback):
                            print("Using fallback branch: %s" % fallback)
                            fallback_branch = fallback
                            break

                if not fallback_branch:
                    print("Default revision %s not found in %s. Bailing." % (default_revision, repo_name))
                    print("Branches found:")
                    for branch in [branch['name'] for branch in result]:
                        print(branch)
                    print("Use the ROOMSERVICE_BRANCHES environment variable to specify a list of fallback branches.")
                    sys.exit()

            add_to_manifest([adding], fallback_branch)

            print("Syncing repository to retrieve project.")
            os.system('repo sync --force-sync %s' % repo_path)
            print("Repository synced!")

            fetch_dependencies(repo_path, fallback_branch)
            print("Done")
            sys.exit()

print("Repository for %s not found in the XOSP Github repository list. If this is in error, you may need to manually add it to your local_manifests/roomservice.xml." % device)
