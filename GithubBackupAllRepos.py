#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File name          : GithubBackupAllRepos.py
# Author             : Podalirius (@podalirius_)
# Date created       : 11 Jan 2022

import argparse
import json
import os
import requests

# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token

def github_http_to_ssh_link(l):
    proto, _, host, username, reponame = l.split('/', 5)
    return "git@github.com:%s/%s.git" % (username, reponame)


def get_repos_from_github(username, token=None, per_page=100):
    # https://docs.github.com/en/rest/reference/repos#releases
    repos, page_number, running = {"repos": []}, 1, True
    while running:
        if token is not None:
            r = requests.get(
                "https://api.github.com/user/repos?per_page=%d&page=%d" % (per_page, page_number),
                headers={"Accept": "application/vnd.github.v3+json", "Authorization": "token %s" % token}
            )
        else:
            print((username, per_page, page_number))
            r = requests.get(
                "https://api.github.com/users/%s/repos?per_page=%d&page=%d" % (username, per_page, page_number),
                headers={"Accept": "application/vnd.github.v3+json"}
            )
        if type(r.json()) == dict:
            if "message" in r.json().keys():
                print(r.json()['message'])
                running = False
        else:
            for repo in r.json():
                repos["repos"].append(repo)
            if len(r.json()) < per_page:
                running = False
            page_number += 1
    print("[+] Detected %d repositories for %s" % (len(repos['repos']), username))
    return repos


def shell_exec(cmd, verbose=False):
    if verbose:
        os.system(cmd)
    else:
        os.popen(cmd).read()


def parseArgs():
    parser = argparse.ArgumentParser(description="A Python script to backup all repos (public or private) of a target user.")
    parser.add_argument("-u", "--username", default=None, required=True, help='Target github username')
    parser.add_argument("-T", "--token", default=None, type=str, help='Github personal access token, necessary to list your private repos.')
    parser.add_argument("-d", "--directory", default='.', required=False, help='Local directory to store repos into.')
    parser.add_argument("-S", "--ssh-key", default=None, required=False, help='SSH key to authenticate with.')
    parser.add_argument("-P", "--pull", default=False, required=False, action='store_true', help='Perform git pull on existing directories.')
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help='Verbose mode. (default: False)')
    return parser.parse_args()


if __name__ == '__main__':
    options = parseArgs()

    if not os.path.exists(options.directory):
        os.makedirs(options.directory, exist_ok=True)
    os.chdir(options.directory)

    repos = get_repos_from_github(options.username, options.token)

    f = open("repos.json", "w")
    f.write(json.dumps(repos, indent=4))
    f.close()

    # Add ssh key if specified
    if options.ssh_key is not None:
        if os.path.exists(options.ssh_key):
            shell_exec("ssh-add %s 2>&1" % options.ssh_key, verbose=options.verbose)
        else:
            print("[!] Could not access SSH key: %s" % options.ssh_key)

    try:
        for repo in repos["repos"]:
            if os.path.exists(repo["name"]):
                if options.pull:
                    print("   [>] Pulling %s" % repo['name'])
                    shell_exec("cd ./%s; git pull --force 2>&1" % repo["name"], verbose=options.verbose)
                else:
                    print("   [>] Cloning %s" % repo['name'])
                    print("      [!] Repository %s already exists locally, use --pull to update it.")
            else:
                print("   [>] Cloning %s" % repo['name'])
                shell_exec("git clone %s 2>&1" % github_http_to_ssh_link(repo['html_url']), verbose=options.verbose)
    except KeyboardInterrupt as e:
        pass

